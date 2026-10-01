# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: core/media_processor.py
# DESCRIPCIÓN: Motor de procesamiento multimedia con FFmpeg y FFprobe.
#              Soporta conversión estereoscópica Side-by-Side (SBS) para videos
#              e imágenes, simulación de profundidad 3D Parallax, aceleración
#              por hardware y lectura de progreso en tiempo real sin congelar la GUI.
# ==============================================================================

import os
import sys
import io
import math
import shutil
import logging
import tempfile
import threading
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, Tuple
from PIL import Image

# Importamos ffmpeg-python para operaciones de sondeo y envoltorio
import ffmpeg

# Importamos el generador de máscaras ópticas y plantillas VR
from core.lens_mask import LensMaskGenerator, LensFormatTemplate

# Configuración del registrador de eventos interno
logger = logging.getLogger("VRShinecon.MediaProcessor")


@dataclass
class MediaItem:
    """
    Representa un elemento individual en la cola de procesamiento.
    Almacena metadatos del medio original y el estado de la conversión.
    """
    file_path: str                 # Ruta absoluta al archivo de origen
    file_name: str                 # Nombre del archivo con extensión
    file_size_bytes: int           # Tamaño del archivo en bytes
    file_size_formatted: str       # Tamaño en formato legible (ej. "45.2 MB")
    media_type: str                # Tipo de medio: 'video' o 'image'
    duration_seconds: float        # Duración en segundos (0.0 para imágenes)
    duration_formatted: str        # Duración en formato "MM:SS" o "HH:MM:SS"
    width: int                     # Ancho en píxeles del medio original
    height: int                    # Alto en píxeles del medio original
    status: str = "pending"        # Estado: 'pending', 'processing', 'completed', 'error', 'cancelled'
    progress: float = 0.0          # Progreso de transcodificación (0.0 a 1.0)
    error_message: str = ""        # Detalle del error si ocurre un fallo
    output_path: str = ""          # Ruta final del archivo convertido


@dataclass
class ConversionOptions:
    """
    Parámetros de configuración aplicados a la conversión multimedia.
    """
    mode: str = "auto"             # Modo de conversión: 'auto' o 'custom'
    template_id: str = "vr_shinecon_1_1" # ID de plantilla óptica ('vr_shinecon_1_1', 'vr180_lens_mask', etc.)
    aspect_mode: str = "1:1"       # Relación de aspecto de cada ojo: '1:1', '4:3', '16:9', 'original', 'fill'
    fit_mode: str = "crop"         # Ajuste en ventana: 'crop' (recorte centrado) o 'fit' (letterbox)
    corner_radius_pct: float = 0.45 # Radio de curvatura de esquinas (0.0 a 1.0)
    margin_pct: float = 0.04       # Margen negro perimetral (0.0 a 0.25)
    center_gap_pct: float = 0.04   # Separación central interpupilar (0.0 a 0.15)
    content_scale: float = 1.0     # Escala de campo de visión (FOV / Zoom): 0.5 a 1.5 (1.0 = 100%)
    sbs_mode: str = "half"         # Formato SBS: 'half' (anamórfico 1080p) o 'full' (doble ancho)
    resolution: str = "1080p"      # Resolución objetivo: 'original', '720p', '1080p', '1440p', '4k'
    container: str = "mp4"         # Extensión del contenedor: 'mp4' o 'mkv'
    crf: int = 18                  # Factor de compresión (14 = máxima nitidez, 28 = alta compresión)
    encoder: str = "cpu"           # Codificador: 'cpu' (libx264), 'nvenc', 'qsv', 'amf'
    parallax_depth: int = 0        # Desplazamiento horizontal en píxeles para disparidad 3D (0 a 30 px)
    audio_codec: str = "copy"      # Manejo de audio: 'copy' (sin pérdida) o 'aac' (estéreo 192k)
    export_directory: str = ""     # Carpeta destino para el archivo resultante


class MediaProcessor:
    """
    Motor central de conversión multimedia utilizando FFmpeg.
    Diseñado para ejecutarse en hilos secundarios (Threading) a fin de mantener
    la interfaz gráfica totalmente fluida y receptiva.
    """

    # Extensiones de video reconocidas comúnmente
    VIDEO_EXTENSIONS = {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
        ".webm", ".m4v", ".ts", ".m2ts", ".vob", ".mpg", ".mpeg"
    }

    # Extensiones de imágenes admitidas
    IMAGE_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"
    }

    def __init__(self) -> None:
        """
        Inicializa el procesador y comprueba la disponibilidad de los ejecutables.
        """
        # Proceso activo de FFmpeg (para control y cancelación segura)
        self._current_process: Optional[subprocess.Popen] = None
        
        # Bandera que indica si el usuario ha solicitado cancelar la tarea
        self._cancel_requested: bool = False

    @staticmethod
    def is_ffmpeg_installed() -> bool:
        """
        Comprueba de forma exhaustiva si el ejecutable de FFmpeg está disponible en el PATH del sistema.
        
        Returns:
            bool: True si FFmpeg puede ejecutarse correctamente, False en caso contrario.
        """
        # Primero buscamos el ejecutable mediante shutil.which
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return False

        try:
            # Ejecutamos una verificación rápida con la bandera -version
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def is_ffprobe_installed() -> bool:
        """
        Verifica si la herramienta de análisis multimedia ffprobe está disponible.
        
        Returns:
            bool: True si ffprobe está listo para usarse.
        """
        ffprobe_bin = shutil.which("ffprobe")
        if not ffprobe_bin:
            return False

        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """
        Determina si la extensión de un archivo corresponde a un formato multimedia soportado.
        
        Args:
            file_path (str): Ruta al archivo evaluado.
            
        Returns:
            bool: True si es un video o imagen compatible.
        """
        _, ext = os.path.splitext(file_path.lower())
        return (ext in cls.VIDEO_EXTENSIONS) or (ext in cls.IMAGE_EXTENSIONS)

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Convierte una cantidad de bytes a una cadena legible (KB, MB, GB).
        
        Args:
            size_bytes (int): Número de bytes.
            
        Returns:
            str: Texto con la magnitud adecuada (ej. "150.3 MB").
        """
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {units[i]}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Formatea una duración en segundos a una representación textual (HH:MM:SS o MM:SS).
        
        Args:
            seconds (float): Tiempo en segundos.
            
        Returns:
            str: Tiempo formateado.
        """
        if seconds <= 0:
            return "00:00"
        total_seconds = int(round(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def inspect_file(self, file_path: str) -> MediaItem:
        """
        Inspecciona un archivo multimedia mediante ffprobe para obtener dimensiones,
        duración, tipo de flujo y metadatos relevantes.
        
        Args:
            file_path (str): Ruta completa al archivo.
            
        Returns:
            MediaItem: Objeto con toda la información extraída.
        """
        # Obtenemos el nombre y tamaño en bytes desde el sistema de archivos
        file_name = os.path.basename(file_path)
        file_size_bytes = os.path.getsize(file_path)
        file_size_formatted = self.format_file_size(file_size_bytes)
        
        # Identificamos el tipo primario según la extensión
        _, ext = os.path.splitext(file_path.lower())
        is_image = ext in self.IMAGE_EXTENSIONS

        media_type = "image" if is_image else "video"
        duration_seconds = 0.0
        duration_formatted = "Imagen estática" if is_image else "Desconocida"
        width = 1920
        height = 1080

        try:
            # Ejecutamos ffprobe mediante el wrapper ffmpeg.probe
            probe_data = ffmpeg.probe(file_path)
            
            # Buscamos el flujo de video principal
            video_streams = [s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"]
            if video_streams:
                primary_stream = video_streams[0]
                width = int(primary_stream.get("width", 1920))
                height = int(primary_stream.get("height", 1080))

                # Extraemos la duración si está presente en el stream o en el formato general
                if not is_image:
                    raw_duration = primary_stream.get("duration")
                    if not raw_duration and "format" in probe_data:
                        raw_duration = probe_data["format"].get("duration")

                    if raw_duration:
                        duration_seconds = float(raw_duration)
                        duration_formatted = self.format_duration(duration_seconds)

        except Exception as error:
            logger.warning("Fallo al inspeccionar %s con ffprobe (%s). Usando valores estimados.", file_name, error)

        return MediaItem(
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            file_size_formatted=file_size_formatted,
            media_type=media_type,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            width=width,
            height=height
        )

    def extract_preview_frame(self, file_path: str, timestamp_sec: float = 1.0) -> Optional[Image.Image]:
        """
        Extrae un fotograma del medio indicado para generar la vista previa.
        Si es una imagen estática, la carga directamente con Pillow.
        Si es un video, extrae un fotograma clave mediante FFmpeg hacia la memoria RAM.
        
        Args:
            file_path (str): Ruta al archivo multimedia.
            timestamp_sec (float): Segundo del video a capturar.
            
        Returns:
            Optional[Image.Image]: Imagen de Pillow en modo RGB, o None en caso de fallo.
        """
        if not os.path.exists(file_path):
            return None

        _, ext = os.path.splitext(file_path.lower())
        if ext in self.IMAGE_EXTENSIONS:
            try:
                img = Image.open(file_path)
                return img.convert("RGB")
            except Exception as err:
                logger.warning("Fallo al abrir imagen %s con Pillow: %s", file_path, err)
                return None

        # Para archivos de video, usamos FFmpeg extrayendo a tubería estándar (pipe)
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = [
            "ffmpeg", "-ss", str(timestamp_sec), "-i", file_path,
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            if res.returncode == 0 and res.stdout:
                return Image.open(io.BytesIO(res.stdout)).convert("RGB")

            # Intento secundario desde el segundo 0.0 si el video es de muy corta duración
            cmd_fallback = [
                "ffmpeg", "-ss", "0.0", "-i", file_path,
                "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"
            ]
            res_fb = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            if res_fb.returncode == 0 and res_fb.stdout:
                return Image.open(io.BytesIO(res_fb.stdout)).convert("RGB")
        except Exception as err:
            logger.warning("Error extrayendo fotograma de %s: %s", file_path, err)

        return None

    def generate_preview(
        self,
        file_path: str,
        options: ConversionOptions,
        target_w: int = 1280,
        target_h: int = 720
    ) -> Optional[Image.Image]:
        """
        Genera la imagen compuesta estereoscópica SBS final para la vista previa en vivo,
        aplicando la plantilla óptica, ajuste de aspecto, esquinas redondeadas y Parallax.
        
        Args:
            file_path (str): Ruta al archivo seleccionado.
            options (ConversionOptions): Opciones y parámetros activos.
            target_w (int): Ancho del lienzo de previsualización.
            target_h (int): Alto del lienzo de previsualización.
            
        Returns:
            Optional[Image.Image]: Imagen compuesta SBS lista para ser renderizada en la GUI.
        """
        frame = self.extract_preview_frame(file_path)
        if frame is None:
            return None

        # Si el modo es automático, usamos la plantilla recomendada para VR Shinecon (1:1 óptico con bordes)
        if options.mode == "auto":
            tmpl = LensMaskGenerator.PRESET_TEMPLATES["vr_shinecon_1_1"]
            aspect_mode = tmpl.aspect_mode
            fit_mode = tmpl.fit_mode
            corner_r = tmpl.corner_radius_pct
            margin = tmpl.margin_pct
            gap = tmpl.center_gap_pct
            parallax = 0
        else:
            aspect_mode = options.aspect_mode
            fit_mode = options.fit_mode
            corner_r = options.corner_radius_pct
            margin = options.margin_pct
            gap = options.center_gap_pct
            parallax = options.parallax_depth

        return LensMaskGenerator.compose_preview_sbs(
            source_frame=frame,
            target_canvas_w=target_w,
            target_canvas_h=target_h,
            aspect_mode=aspect_mode,
            fit_mode=fit_mode,
            corner_radius_pct=corner_r,
            margin_pct=margin,
            center_gap_pct=gap,
            parallax_px=parallax
        )

    def _determine_target_dimensions(self, input_width: int, input_height: int, resolution_opt: str) -> Tuple[int, int]:
        """
        Calcula la resolución objetivo del video o imagen final de acuerdo con la opción elegida.
        Garantiza que tanto el ancho como el alto sean números pares (múltiplos de 2 requeridos por h264).
        
        Args:
            input_width (int): Ancho original.
            input_height (int): Alto original.
            resolution_opt (str): Clave de resolución ('original', '720p', '1080p', '1440p', '4k').
            
        Returns:
            Tuple[int, int]: (ancho_objetivo, alto_objetivo).
        """
        resolutions_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "1440p": (2560, 1440),
            "4k": (3840, 2160)
        }

        if resolution_opt in resolutions_map:
            target_w, target_h = resolutions_map[resolution_opt]
        else:
            target_w, target_h = input_width, input_height

        # Aseguramos múltiplos de 2 para compatibilidad estricta con códecs H.264 / H.265
        target_w = target_w - (target_w % 2)
        target_h = target_h - (target_h % 2)

        return target_w, target_h

    def _build_filter_complex(
        self,
        target_w: int,
        target_h: int,
        options: ConversionOptions
    ) -> Tuple[str, Optional[str]]:
        """
        Construye la expresión de filtros de FFmpeg (-filter_complex) para generar
        la composición estereoscópica SBS adaptada a visores pasivos con esquinas redondeadas.
        
        Args:
            target_w (int): Ancho total deseado.
            target_h (int): Alto total deseado.
            options (ConversionOptions): Opciones y parámetros activos.
            
        Returns:
            Tuple[str, Optional[str]]: (filter_complex_str, ruta_mascara_png_temporal_o_None).
        """
        tmpl_id = options.template_id if options.template_id in LensMaskGenerator.PRESET_TEMPLATES else "vr_shinecon_1_1"
        tmpl = LensMaskGenerator.PRESET_TEMPLATES[tmpl_id]

        if options.mode == "auto":
            aspect_mode = options.aspect_mode if options.aspect_mode else tmpl.aspect_mode
            fit_mode = options.fit_mode if options.fit_mode else tmpl.fit_mode
            corner_r = tmpl.corner_radius_pct
            margin_pct = tmpl.margin_pct
            gap_pct = tmpl.center_gap_pct
            content_scale = options.content_scale if hasattr(options, "content_scale") and options.content_scale != 1.0 else tmpl.content_scale
            parallax = options.parallax_depth
            sbs_mode = options.sbs_mode
        else:
            aspect_mode = options.aspect_mode
            fit_mode = options.fit_mode
            corner_r = options.corner_radius_pct
            margin_pct = options.margin_pct
            gap_pct = options.center_gap_pct
            content_scale = getattr(options, "content_scale", 1.0)
            parallax = options.parallax_depth
            sbs_mode = options.sbs_mode

        # En Full SBS cada mitad es target_w; en Half SBS cada mitad es target_w // 2
        half_w = target_w if sbs_mode == "full" else (target_w // 2)
        half_w = half_w - (half_w % 2)
        total_w = half_w * 2

        # Calculamos la geometría de la ventana de cada ojo dentro del canvas total
        x_l, y_l, x_r, y_r, eye_w, eye_h = LensMaskGenerator.calculate_eye_dimensions(
            total_w, target_h, margin_pct, gap_pct
        )
        eye_w = eye_w - (eye_w % 2)
        eye_h = eye_h - (eye_h % 2)

        # Márgenes de encaje en cada mitad
        pad_x_left = x_l
        pad_y = y_l
        pad_x_right = x_r - half_w

        # Escala de campo de visión (FOV / Zoom)
        scale_val = max(0.5, min(content_scale, 1.5))
        scaled_w = int(eye_w * scale_val)
        scaled_w = max(2, scaled_w - (scaled_w % 2))
        scaled_h = int(eye_h * scale_val)
        scaled_h = max(2, scaled_h - (scaled_h % 2))

        # Filtro de transformación de aspecto y escala para la ventana del ojo
        if fit_mode == "fit":
            # 100% de la imagen visible, sin recortes (Letterbox / Pillarbox)
            if scale_val <= 1.0:
                fit_filter = (
                    f"scale={scaled_w}:{scaled_h}:force_original_aspect_ratio=decrease,"
                    f"pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
                )
            else:
                fit_filter = (
                    f"scale={scaled_w}:{scaled_h}:force_original_aspect_ratio=decrease,"
                    f"crop={eye_w}:{eye_h}:(iw-ow)/2:(ih-oh)/2,"
                    f"pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
                )
        elif aspect_mode == "1:1" and fit_mode == "crop":
            crop_base = "crop=min(iw\\,ih):min(iw\\,ih)"
            if scale_val <= 1.0:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
            else:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,crop={eye_w}:{eye_h}:(iw-ow)/2:(ih-oh)/2"
        elif aspect_mode == "4:3" and fit_mode == "crop":
            crop_base = "crop=if(gt(iw/ih\\,4/3)\\,ih*4/3\\,iw):if(gt(iw/ih\\,4/3)\\,ih\\,iw*3/4)"
            if scale_val <= 1.0:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
            else:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,crop={eye_w}:{eye_h}:(iw-ow)/2:(ih-oh)/2"
        elif aspect_mode == "16:9" and fit_mode == "crop":
            crop_base = "crop=if(gt(iw/ih\\,16/9)\\,ih*16/9\\,iw):if(gt(iw/ih\\,16/9)\\,ih\\,iw*9/16)"
            if scale_val <= 1.0:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
            else:
                fit_filter = f"{crop_base},scale={scaled_w}:{scaled_h}:flags=lanczos,crop={eye_w}:{eye_h}:(iw-ow)/2:(ih-oh)/2"
        else:
            # Modo fill
            if scale_val <= 1.0:
                fit_filter = f"scale={scaled_w}:{scaled_h}:flags=lanczos,pad={eye_w}:{eye_h}:(ow-iw)/2:(oh-ih)/2:black"
            else:
                fit_filter = f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={eye_w}:{eye_h}:(iw-ow)/2:(ih-oh)/2"

        # Aplicación de simulación de profundidad 3D Parallax si es mayor a 0
        if parallax > 0:
            p = min(parallax, 50)
            p = p - (p % 2)
            left_eye_filter = f"[0:v]{fit_filter},crop=iw-{p}:ih:{p}:0,scale={eye_w}:{eye_h}:flags=lanczos[eye_l];"
            right_eye_filter = f"[0:v]{fit_filter},crop=iw-{p}:ih:0:0,scale={eye_w}:{eye_h}:flags=lanczos[eye_r];"
        else:
            left_eye_filter = f"[0:v]{fit_filter}[eye_l];"
            right_eye_filter = f"[0:v]{fit_filter}[eye_r];"

        # Construcción de las dos mitades mediante pad y combinación horizontal (hstack)
        padding_filter = (
            f"[eye_l]pad={half_w}:{target_h}:{pad_x_left}:{pad_y}:black[l_padded];"
            f"[eye_r]pad={half_w}:{target_h}:{pad_x_right}:{pad_y}:black[r_padded];"
            f"[l_padded][r_padded]hstack=inputs=2[sbs]"
        )

        temp_mask_path: Optional[str] = None

        # Si se requieren esquinas redondeadas, generamos la máscara y la superponemos con overlay
        if corner_r > 0:
            mask_img = LensMaskGenerator.generate_mask_image(
                total_w, target_h, corner_r, margin_pct, gap_pct
            )
            temp_mask_path = os.path.join(tempfile.gettempdir(), f"vr_mask_{os.getpid()}_{id(options)}.png")
            mask_img.save(temp_mask_path, "PNG")

            overlay_filter = ";[sbs][1:v]overlay=0:0[outv]"
        else:
            overlay_filter = ""
            # Reemplazamos [sbs] con [outv]
            padding_filter = padding_filter.replace("[sbs]", "[outv]")

        full_filter = left_eye_filter + right_eye_filter + padding_filter + overlay_filter
        return full_filter, temp_mask_path

    def _select_video_encoder(self, encoder_opt: str) -> Tuple[str, list]:
        """
        Selecciona el códec de video y parámetros adicionales según el hardware elegido.
        
        Args:
            encoder_opt (str): 'cpu', 'nvenc', 'qsv' o 'amf'.
            
        Returns:
            Tuple[str, list]: Nombre del códec en FFmpeg y argumentos extra.
        """
        if encoder_opt == "nvenc":
            return "h264_nvenc", ["-preset", "p4", "-tune", "hq"]
        elif encoder_opt == "qsv":
            return "h264_qsv", ["-preset", "medium"]
        elif encoder_opt == "amf":
            return "h264_amf", ["-quality", "quality"]
        else:
            # CPU por defecto con libx264 (máxima calidad y compatibilidad universal)
            return "libx264", ["-preset", "medium", "-pix_fmt", "yuv420p"]

    def _generate_output_path(self, input_path: str, export_dir: str, sbs_mode: str, container: str, is_image: bool) -> str:
        """
        Genera una ruta única para el archivo resultante, evitando sobrescribir medios existentes.
        
        Args:
            input_path (str): Ruta original.
            export_dir (str): Directorio de destino.
            sbs_mode (str): 'half' o 'full'.
            container (str): Extensión deseada ('mp4', 'mkv', 'jpg', 'png').
            is_image (bool): True si es una imagen estática.
            
        Returns:
            str: Ruta completa al archivo de salida que no colisiona con otros archivos.
        """
        base_name, _ = os.path.splitext(os.path.basename(input_path))
        sbs_tag = "HalfSBS" if sbs_mode == "half" else "FullSBS"
        ext = ".jpg" if (is_image and container in ["mp4", "mkv"]) else f".{container.lstrip('.')}"
        
        target_name = f"{base_name}_{sbs_tag}{ext}"
        candidate_path = os.path.join(export_dir, target_name)

        # Si ya existe un archivo con ese nombre, añadimos un contador incremental
        counter = 1
        while os.path.exists(candidate_path):
            candidate_path = os.path.join(export_dir, f"{base_name}_{sbs_tag}_{counter}{ext}")
            counter += 1

        return candidate_path

    def cancel(self) -> None:
        """
        Solicita la detención inmediata del proceso actual de conversión en ejecución.
        Termina el subproceso de FFmpeg de forma limpia.
        """
        self._cancel_requested = True
        if self._current_process is not None:
            try:
                logger.info("Cancelación solicitada. Terminando proceso de FFmpeg...")
                self._current_process.terminate()
                self._current_process.kill()
            except Exception as error:
                logger.warning("Error al terminar proceso FFmpeg: %s", error)

    def convert_item(
        self,
        item: MediaItem,
        options: ConversionOptions,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Ejecuta la conversión de un elemento multimedia individual (video o imagen).
        Supervisa la salida de FFmpeg en tiempo real para reportar el avance porcentual.
        
        Args:
            item (MediaItem): Elemento a procesar.
            options (ConversionOptions): Opciones y parámetros de transcodificación.
            progress_callback (Callable[[float, str], None], opcional): Función que recibe (progreso_0_a_1, texto_estado).
            log_callback (Callable[[str], None], opcional): Función para registrar mensajes de log en la consola.
            
        Returns:
            bool: True si la conversión culminó exitosamente, False si falló o fue cancelada.
        """
        # Restablecemos la bandera de cancelación
        self._cancel_requested = False
        item.status = "processing"
        item.progress = 0.0

        def log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        # Verificamos que el archivo original exista
        if not os.path.exists(item.file_path):
            err = f"El archivo de origen no existe: {item.file_path}"
            item.status = "error"
            item.error_message = err
            log(f"[ERROR] {err}")
            return False

        # Verificamos la carpeta de destino
        export_dir = options.export_directory or os.path.dirname(item.file_path)
        os.makedirs(export_dir, exist_ok=True)

        is_image = (item.media_type == "image")

        # Determinamos dimensiones y filtros
        if options.mode == "auto":
            # Modo automático optimizado para VR Shinecon: Half SBS 1080p, CRF 18
            target_w, target_h = 1920, 1080
            sbs_mode = "half"
            crf_val = 18
            encoder_name, encoder_args = "libx264", ["-preset", "medium", "-pix_fmt", "yuv420p"]
            container = "mp4"
            audio_args = ["-c:a", "copy"]
            parallax = 0
        else:
            # Modo personalizado con todos los parámetros especificados por el usuario
            target_w, target_h = self._determine_target_dimensions(item.width, item.height, options.resolution)
            sbs_mode = options.sbs_mode
            crf_val = options.crf
            encoder_name, encoder_args = self._select_video_encoder(options.encoder)
            container = options.container
            parallax = options.parallax_depth

            if options.audio_codec == "copy":
                audio_args = ["-c:a", "copy"]
            else:
                audio_args = ["-c:a", "aac", "-b:a", "192k"]

        # Generamos la ruta de salida
        output_path = self._generate_output_path(item.file_path, export_dir, sbs_mode, container, is_image)
        item.output_path = output_path

        # Si es una imagen estática, procesamos directamente con Pillow para máxima fidelidad visual y rapidez
        if is_image:
            log(f"Procesando imagen estática '{item.file_name}' a SBS ({sbs_mode.upper()})...")
            try:
                src_img = Image.open(item.file_path).convert("RGB")
                if options.mode == "auto":
                    tmpl = LensMaskGenerator.PRESET_TEMPLATES["vr_shinecon_1_1"]
                    aspect_mode = tmpl.aspect_mode
                    fit_mode = tmpl.fit_mode
                    corner_r = tmpl.corner_radius_pct
                    margin = tmpl.margin_pct
                    gap = tmpl.center_gap_pct
                    parallax = 0
                else:
                    aspect_mode = options.aspect_mode
                    fit_mode = options.fit_mode
                    corner_r = options.corner_radius_pct
                    margin = options.margin_pct
                    gap = options.center_gap_pct
                    parallax = options.parallax_depth

                sbs_img = LensMaskGenerator.compose_preview_sbs(
                    source_frame=src_img,
                    target_canvas_w=target_w,
                    target_canvas_h=target_h,
                    aspect_mode=aspect_mode,
                    fit_mode=fit_mode,
                    corner_radius_pct=corner_r,
                    margin_pct=margin,
                    center_gap_pct=gap,
                    parallax_px=parallax
                )
                sbs_img.save(output_path, quality=95)
                item.status = "completed"
                item.progress = 1.0
                log(f"[ÉXITO] Imagen convertida exitosamente en: {output_path}")
                if progress_callback:
                    progress_callback(1.0, "100% - Completado con éxito")
                return True
            except Exception as ex_img:
                log(f"[ERROR] Error procesando imagen '{item.file_name}': {ex_img}")
                item.status = "error"
                item.error_message = str(ex_img)
                return False

        # Construimos el complejo de filtros para la visión SBS y la máscara de esquinas
        filter_str, temp_mask_path = self._build_filter_complex(target_w, target_h, options)

        log(f"Iniciando transcodificación de '{item.file_name}' a SBS ({sbs_mode.upper()})...")
        log(f"Resolución de salida configurada: {target_w}x{target_h} | Calidad CRF: {crf_val}")

        # Construimos la línea de comandos de FFmpeg
        cmd = ["ffmpeg", "-y", "-i", item.file_path]
        if temp_mask_path and os.path.exists(temp_mask_path):
            cmd.extend(["-i", temp_mask_path])

        cmd.extend(["-filter_complex", filter_str, "-map", "[outv]"])
        cmd.extend(["-map", "0:a?", "-c:v", encoder_name, "-crf", str(crf_val)])
        cmd.extend(encoder_args)
        cmd.extend(audio_args)
        cmd.extend(["-progress", "pipe:1", "-nostats", output_path])

        logger.debug("Comando FFmpeg: %s", " ".join(cmd))

        # Configuración para evitar abrir ventanas negras de terminal en Windows
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        try:
            # Lanzamos el subproceso de FFmpeg
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )

            # Drenamos stderr en un hilo daemon secundario para evitar interbloqueo (deadlock) del búfer del SO
            stderr_lines = []
            def _drain_stderr() -> None:
                try:
                    for err_line in self._current_process.stderr:
                        stderr_lines.append(err_line)
                except Exception:
                    pass

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            # Monitoreo de progreso en tiempo real si es video
            if not is_image and item.duration_seconds > 0:
                current_time_sec = 0.0
                current_speed = "1.0x"
                current_fps = "0"

                # Leemos la salida clave-valor generada por -progress pipe:1
                for line in self._current_process.stdout:
                    if self._cancel_requested:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()

                        if k == "out_time_us":
                            try:
                                # out_time_us viene en microsegundos
                                current_time_sec = float(v) / 1_000_000.0
                            except ValueError:
                                pass
                        elif k == "fps":
                            current_fps = v
                        elif k == "speed":
                            current_speed = v
                        elif k == "progress":
                            # Calculamos la proporción de avance
                            frac = min(max(current_time_sec / item.duration_seconds, 0.0), 0.99)
                            item.progress = frac
                            pct = int(frac * 100)
                            status_text = f"{pct}% | Velocidad: {current_speed} | FPS: {current_fps}"
                            if progress_callback:
                                progress_callback(frac, status_text)

            # Esperamos a que el subproceso finalice
            self._current_process.wait()
            stderr_thread.join(timeout=1.0)
            stderr_output = "".join(stderr_lines)
            return_code = self._current_process.returncode

            # Verificamos si fue cancelado
            if self._cancel_requested:
                item.status = "cancelled"
                item.progress = 0.0
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                log(f"[CANCELADO] La conversión de '{item.file_name}' fue interrumpida por el usuario.")
                if progress_callback:
                    progress_callback(0.0, "Conversión cancelada")
                return False

            # Verificamos código de salida de FFmpeg
            if return_code != 0:
                err_msg = f"FFmpeg retornó código de error {return_code}."
                item.status = "error"
                item.error_message = err_msg
                log(f"[ERROR] Falló la conversión de '{item.file_name}': {err_msg}")
                if stderr_output:
                    tail_err = "\n".join(stderr_output.strip().splitlines()[-4:])
                    log(f"Detalle técnico:\n{tail_err}")
                return False

            # Conversión completada con éxito
            item.status = "completed"
            item.progress = 1.0
            log(f"[ÉXITO] Archivo convertido exitosamente en: {output_path}")
            if progress_callback:
                progress_callback(1.0, "100% - Completado con éxito")
            return True

        except Exception as ex:
            item.status = "error"
            item.error_message = str(ex)
            log(f"[ERROR EXCEPCIÓN] Error inesperado procesando '{item.file_name}': {ex}")
            return False

        finally:
            self._current_process = None
            # Limpiamos el archivo temporal de máscara si fue creado
            if temp_mask_path and os.path.exists(temp_mask_path):
                try:
                    os.remove(temp_mask_path)
                except OSError:
                    pass
