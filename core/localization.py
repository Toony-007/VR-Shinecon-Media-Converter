# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: core/localization.py
# DESCRIPCIÓN: Sistema de internacionalización y soporte multilingüe en tiempo real.
#              Permite cambiar entre Español e Inglés sin reiniciar la aplicación.
# ==============================================================================

from typing import Callable, Dict, List, Any


class LocalizationManager:
    """
    Gestor de traducciones y textos de la interfaz gráfica.
    Mantiene un diccionario central de cadenas de texto y notifica a los observadores
    cuando el usuario cambia el idioma seleccionado.
    """

    # Diccionario maestro de traducciones categorizado por código de idioma
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "es": {
            # Título principal de la aplicación y cabeceras
            "app_title": "VR Shinecon Media Converter - 2D a 3D SBS",
            "app_subtitle": "Conversor Estereoscópico Side-by-Side para Visores VR Pasivos",
            
            # Nombres de las pestañas
            "tab_conversion": "Conversión",
            "tab_streaming": "Streaming en Vivo",
            "tab_settings": "Configuración",
            "tab_info": "Información VR",

            # Pestaña Conversión - Sección de importación y cola
            "import_files": "Importar Archivo(s)",
            "clear_queue": "Limpiar Lista",
            "queue_title": "Cola de Procesamiento Multimedia (Videos e Imágenes)",
            "col_file": "Archivo",
            "col_type": "Tipo",
            "col_duration": "Duración / Tamaño",
            "col_status": "Estado",
            "status_pending": "Pendiente",
            "status_processing": "Procesando...",
            "status_completed": "Completado",
            "status_error": "Error",
            "status_cancelled": "Cancelado",
            "no_files_queued": "No hay archivos en la cola. Haz clic en 'Importar Archivo(s)' para comenzar.",

            # Pestaña Conversión - Modos de Exportación
            "export_mode_title": "Modo de Exportación",
            "mode_auto": "Automático (Recomendado VR Shinecon)",
            "mode_custom": "Personalizado (Opciones Avanzadas)",
            "auto_description": (
                "Preset óptimo para gafas VR pasivas (VR Shinecon, Cardboard, etc.):\n"
                "• Formato: Half SBS (1080p, 16:9 ajustado a cada ojo)\n"
                "• Códec de Video: H.264 (Compatibilidad total con smartphones)\n"
                "• Calidad: CRF 18 (Alta nitidez visual preservada)\n"
                "• Audio: Copia directa sin pérdidas de la pista original"
            ),

            # Pestaña Conversión - Opciones Avanzadas
            "advanced_options_title": "Parámetros Avanzados de Conversión",
            "label_sbs_type": "Formato Estereoscópico SBS:",
            "opt_sbs_half": "Half SBS (Anamórfico 1080p - Recomendado para visores)",
            "opt_sbs_full": "Full SBS (Resolución Completa Doble Ancho)",
            "label_resolution": "Resolución de Salida:",
            "opt_res_original": "Mantener Original",
            "opt_res_1080p": "1080p Full HD (1920x1080)",
            "opt_res_720p": "720p HD (1280x720)",
            "opt_res_1440p": "1440p 2K (2560x1440)",
            "opt_res_4k": "2160p 4K (3840x2160)",
            "label_container": "Formato Contenedor:",
            "label_encoder": "Aceleración / Codificador:",
            "opt_enc_cpu": "CPU - libx264 (Universal / Máxima compatibilidad)",
            "opt_enc_nvenc": "NVIDIA NVENC (Aceleración GPU Ultra Rápida)",
            "opt_enc_qsv": "Intel QSV (Aceleración Quick Sync)",
            "opt_enc_amf": "AMD AMF (Aceleración Radeon)",
            "label_quality": "Calidad de Compresión (CRF):",
            "quality_tooltip": "Valores menores = Mayor calidad y mayor peso. Recomendado: 18 a 22.",
            "label_parallax": "Profundidad 3D / Parallax (Desplazamiento Óptico):",
            "parallax_none": "0 px (2D Plano Duplicado)",
            "parallax_subtle": "10 px (Profundidad Sutil)",
            "parallax_medium": "18 px (Profundidad Media)",
            "parallax_strong": "26 px (Profundidad Intensa)",
            "label_audio": "Gestión de Audio:",
            "opt_audio_copy": "Copiar Pista Original (Sin Pérdida)",
            "opt_audio_aac": "Re-codificar a AAC Estéreo (192 kbps)",

            # Pestaña Conversión - Acciones y Progreso
            "btn_start_conversion": "Iniciar Conversión",
            "btn_cancel_conversion": "Cancelar",
            "btn_live_preview": "🔍 Vista Previa en Vivo",
            "btn_enlarge_preview": "⛶ Ampliar Vista Previa",
            "btn_refresh_preview": "🔄 Actualizar Vista",
            "preview_title": "Vista Previa de Salida Estereoscópica (SBS)",
            "preview_modal_title": "Vista Previa SBS - VR Shinecon Media Converter",
            "preview_no_file": "Selecciona o importa un archivo multimedia para generar la vista previa.",
            "preview_loading": "Generando fotograma de vista previa...",
            "progress_title": "Progreso de Transcodificación:",
            "progress_overall": "Progreso Total:",
            "console_title": "Consola de Estado y Registro (Log):",
            "log_ready": "Sistema inicializado. Listo para procesar archivos multimedia.",

            # Plantillas y Control de Bordes / Esquinas
            "label_template": "Plantilla de Formato Óptico:",
            "tmpl_cinema_full_name": "Cine Virtual Completo (100% Contenido / Sin Recorte)",
            "tmpl_cinema_full_desc": "Muestra el 100% del video o pantalla sin recortar bordes. Pantalla de cine flotante con bordes redondeados y escala ajustable.",
            "tmpl_shinecon_1_1_name": "VR Shinecon Óptico (Cuadrado 1:1)",
            "tmpl_shinecon_1_1_desc": "Ajuste cuadrado 1:1 centrado con esquinas redondeadas. Elimina el estiramiento horizontal y se adapta a las lentes de VR Shinecon.",
            "tmpl_vr180_name": "Máscara de Visor VR180 / Barril Ocular",
            "tmpl_vr180_desc": "Curvatura pronunciada en las esquinas que imita la máscara física de los visores de realidad virtual.",
            "tmpl_cinema_name": "Cine Virtual VR (16:9 Flotante)",
            "tmpl_cinema_desc": "Pantalla panorámica cinematográfica flotando en espacio negro con esquinas redondeadas suaves.",
            "tmpl_4_3_name": "Formato Óptico 4:3",
            "tmpl_4_3_desc": "Proporción 4:3 equilibrada con esquinas curvadas, ideal para pantallas de teléfonos grandes.",
            "tmpl_fullscreen_name": "Half SBS Estándar (Pantalla Completa)",
            "tmpl_fullscreen_desc": "Sin marco ni esquinas redondeadas. Anamórfico tradicional a pantalla completa.",
            "tmpl_custom_name": "Personalizado (Ajuste Libre)",
            "tmpl_custom_desc": "Personaliza el radio de esquinas, aspecto y márgenes de borde a tu gusto.",

            "label_aspect": "Relación de Aspecto de Imagen:",
            "opt_aspect_1_1": "1:1 Cuadrado (Óptimo VR - No estirado)",
            "opt_aspect_4_3": "4:3 Equilibrado",
            "opt_aspect_16_9": "16:9 Panorámico",
            "opt_aspect_original": "Proporción Original",
            "opt_aspect_fill": "Estirar a Ventana",

            "label_fit_mode": "Modo de Ajuste en Ventana:",
            "opt_fit_crop": "Rellenar Lente (Recorte inmersivo)",
            "opt_fit_letterbox": "Ajustar al Marco (100% Visible / Sin recortes)",

            "label_content_scale": "Tamaño de Pantalla / Escala (FOV):",
            "scale_indicator": "{val}% (Campo de Visión)",

            "label_corner_radius": "Curvatura de Esquinas (Radio Lente):",
            "label_margin": "Margen / Borde Negro Exterior:",
            "label_center_gap": "Separación Central Interpupilar:",

            # Pestaña Streaming en Tiempo Real
            "stream_source_title": "Fuente de Captura en Vivo",
            "stream_source_screen": "Pantalla Completa (Monitores)",
            "stream_source_window": "Ventana de Aplicación (Navegador, VLC, etc.)",
            "stream_btn_refresh_windows": "🔄 Actualizar Ventanas",
            "stream_optical_title": "Calibración Óptica y Plantilla SBS",
            "stream_scale_label": "Escala / FOV:",
            "stream_fit_label": "Modo de Ajuste:",
            "stream_fps_label": "Tasa de Cuadros (FPS):",
            "stream_profile_label": "Calidad y Rendimiento:",
            "stream_profile_1080p_ultra": "🌟 1080p Ultra (60 FPS / Máxima Nitidez)",
            "stream_profile_1080p_balanced": "⚖️ 1080p Equilibrado (30 FPS / Alta Calidad)",
            "stream_profile_720p_fast": "⚡ 720p HD Fluido (60 FPS / Baja Latencia Wi-Fi)",
            "stream_profile_720p_low": "📱 720p Red Básica (30 FPS / Menor Consumo)",
            "stream_btn_start_projection": "🚀 Iniciar Proyección en Pantalla Completa (F11)",
            "stream_zoom_hint": "💡 Atajos en Pantalla Completa: Rueda del Ratón o teclas + / - para Zoom, 0 para restablecer.",
            "stream_web_title": "Servidor Web para Celular (Sin Cables ni Apps)",
            "stream_web_switch": "Transmitir por Wi-Fi al Celular",
            "stream_web_url_label": "Abre este enlace en el navegador del celular:",
            "stream_web_copy": "📋 Copiar Enlace",
            "stream_web_status_off": "Servidor Web Detenido",
            "stream_web_status_on": "🟢 Transmitiendo en vivo en la red local",
            "stream_help_note": "💡 Conecta tu celular al mismo Wi-Fi que la PC, abre el enlace en Chrome/Safari y presiona 'Pantalla Completa VR'.",

            # Pestaña Configuración
            "settings_general_title": "Configuración General del Sistema",
            "label_export_dir": "Carpeta de Destino para Exportaciones:",
            "btn_browse": "Explorar...",
            "btn_open_folder": "Abrir Carpeta",
            "label_default_crf": "Calidad por Defecto (CRF):",
            "label_language": "Idioma de la Interfaz:",
            "label_theme": "Tema Visual:",
            "theme_dark": "Modo Oscuro",
            "theme_light": "Modo Claro",
            "theme_system": "Sincronizar con Sistema",
            "btn_save_settings": "Guardar Configuración",
            "settings_saved_msg": "¡Configuraciones guardadas exitosamente en config.json!",

            # Pestaña Información VR
            "info_title": "¿Cómo funciona la tecnología SBS para VR Shinecon?",
            "info_body": (
                "Las gafas de realidad virtual pasivas como VR Shinecon o Google Cardboard no poseen pantallas "
                "electrónicas integradas; utilizan la pantalla de tu teléfono móvil colocada detrás de dos lentes "
                "biconvexas.\n\n"
                "¿Qué es Side-by-Side (SBS)?\n"
                "Es un formato en el que una imagen o video se divide en dos mitades horizontales (izquierda y derecha). "
                "El ojo izquierdo observa la mitad izquierda y el ojo derecho la mitad derecha.\n\n"
                "• Half SBS (HSBS): Cada imagen se comprime al 50% de su ancho. Al verse a través de las lentes, "
                "el cerebro las expande al tamaño correcto (relación 16:9). Es el formato estándar soportado por "
                "reproductores VR en Android e iOS como VR Player, VLC VR, GizmoVR, etc.\n\n"
                "• Simulación de Profundidad 3D (Parallax): Nuestra aplicación incorpora un algoritmo que genera una "
                "disparidad horizontal controlada entre las dos imágenes, permitiendo que tu cerebro perciba volumen "
                "y profundidad estereoscópica realista en lugar de un video plano."
            ),

            # Diálogos y Errores
            "dialog_error_title": "Error del Sistema",
            "dialog_warning_title": "Advertencia",
            "dialog_success_title": "Operación Exitosa",
            "dialog_info_title": "Información",
            "ffmpeg_missing_title": "FFmpeg no encontrado",
            "ffmpeg_missing_msg": (
                "No se pudo detectar el ejecutable de FFmpeg en el sistema o en el PATH.\n\n"
                "Para convertir videos a formato SBS, FFmpeg es indispensable.\n"
                "Por favor descarga FFmpeg e intégralo a las variables de entorno del sistema."
            ),
            "no_files_selected_msg": "Por favor importa al menos un archivo de video o imagen para convertir.",
            "conversion_finished_title": "¡Proceso Completado!",
            "conversion_finished_msg": "Se han convertido satisfactoriamente todos los archivos de la cola.",
            "conversion_cancelled_msg": "La conversión ha sido cancelada por el usuario.",
            "confirm_clear_queue": "¿Estás seguro de que deseas limpiar toda la cola de archivos?",
            "confirm_title": "Confirmación",
            "btn_yes": "Sí",
            "btn_no": "No",
            "btn_ok": "Aceptar"
        },
        "en": {
            # Main application title and headers
            "app_title": "VR Shinecon Media Converter - 2D to 3D SBS",
            "app_subtitle": "Stereoscopic Side-by-Side Converter for Passive VR Headsets",

            # Tab names
            "tab_conversion": "Conversion",
            "tab_streaming": "Live Streaming",
            "tab_settings": "Settings",
            "tab_info": "VR Guide",

            # Conversion Tab - Import & Queue
            "import_files": "Import File(s)",
            "clear_queue": "Clear List",
            "queue_title": "Multimedia Processing Queue (Videos & Images)",
            "col_file": "File",
            "col_type": "Type",
            "col_duration": "Duration / Size",
            "col_status": "Status",
            "status_pending": "Pending",
            "status_processing": "Processing...",
            "status_completed": "Completed",
            "status_error": "Error",
            "status_cancelled": "Cancelled",
            "no_files_queued": "No files in queue. Click 'Import File(s)' to get started.",

            # Conversion Tab - Export Modes
            "export_mode_title": "Export Mode",
            "mode_auto": "Automatic (Recommended for VR Shinecon)",
            "mode_custom": "Custom (Advanced Options)",
            "auto_description": (
                "Optimal preset for passive VR headsets (VR Shinecon, Cardboard, etc.):\n"
                "• Format: Half SBS (1080p, 16:9 fitted to each eye)\n"
                "• Video Codec: H.264 (Maximum smartphone compatibility)\n"
                "• Quality: CRF 18 (Preserved high visual sharpness)\n"
                "• Audio: Direct lossless stream copy"
            ),

            # Conversion Tab - Advanced Options
            "advanced_options_title": "Advanced Conversion Parameters",
            "label_sbs_type": "SBS Stereoscopic Format:",
            "opt_sbs_half": "Half SBS (Anamorphic 1080p - Recommended for headsets)",
            "opt_sbs_full": "Full SBS (Full Double-Width Resolution)",
            "label_resolution": "Output Resolution:",
            "opt_res_original": "Keep Original",
            "opt_res_1080p": "1080p Full HD (1920x1080)",
            "opt_res_720p": "720p HD (1280x720)",
            "opt_res_1440p": "1440p 2K (2560x1440)",
            "opt_res_4k": "2160p 4K (3840x2160)",
            "label_container": "Container Format:",
            "label_encoder": "Hardware / Codec:",
            "opt_enc_cpu": "CPU - libx264 (Universal / Maximum Compatibility)",
            "opt_enc_nvenc": "NVIDIA NVENC (Ultra Fast GPU Acceleration)",
            "opt_enc_qsv": "Intel QSV (Quick Sync Acceleration)",
            "opt_enc_amf": "AMD AMF (Radeon Acceleration)",
            "label_quality": "Compression Quality (CRF):",
            "quality_tooltip": "Lower values = Higher quality and larger file size. Recommended: 18 to 22.",
            "label_parallax": "3D Parallax Depth (Optical Shift):",
            "parallax_none": "0 px (Flat 2D Duplicate)",
            "parallax_subtle": "10 px (Subtle Depth)",
            "parallax_medium": "18 px (Medium Depth)",
            "parallax_strong": "26 px (Strong Depth)",
            "label_audio": "Audio Management:",
            "opt_audio_copy": "Copy Original Track (Lossless)",
            "opt_audio_aac": "Re-encode to AAC Stereo (192 kbps)",

            # Conversion Tab - Actions & Progress
            "btn_start_conversion": "Start Conversion",
            "btn_cancel_conversion": "Cancel",
            "btn_live_preview": "🔍 Live Preview",
            "btn_enlarge_preview": "⛶ Enlarge Preview",
            "btn_refresh_preview": "🔄 Refresh Preview",
            "preview_title": "Stereoscopic (SBS) Output Preview",
            "preview_modal_title": "SBS Preview - VR Shinecon Media Converter",
            "preview_no_file": "Select or import a media file to generate preview.",
            "preview_loading": "Generating live preview frame...",
            "progress_title": "Transcoding Progress:",
            "progress_overall": "Overall Progress:",
            "console_title": "Status Console and Logs:",
            "log_ready": "System initialized. Ready to process multimedia files.",

            # Templates & Rounded Corners / Border Control
            "label_template": "Optical Format Template:",
            "tmpl_cinema_full_name": "Full Virtual Cinema (100% Content / No Crop)",
            "tmpl_cinema_full_desc": "Displays 100% of the video or screen without edge clipping. Floating cinema screen with rounded corners and adjustable FOV scale.",
            "tmpl_shinecon_1_1_name": "VR Shinecon Optical (Square 1:1)",
            "tmpl_shinecon_1_1_desc": "Centered 1:1 square fit with rounded corners. Eliminates horizontal stretching and fits VR Shinecon lenses.",
            "tmpl_vr180_name": "VR180 Headset Mask / Eyepiece Barrel",
            "tmpl_vr180_desc": "Deep curved corners simulating the physical eyepiece mask of commercial VR headsets.",
            "tmpl_cinema_name": "Virtual Cinema VR (Floating 16:9)",
            "tmpl_cinema_desc": "Widescreen cinema screen floating in black space with smooth rounded corners.",
            "tmpl_4_3_name": "Optical 4:3 Format",
            "tmpl_4_3_desc": "Balanced 4:3 aspect with curved corners, ideal for large smartphones.",
            "tmpl_fullscreen_name": "Half SBS Standard (Full Screen)",
            "tmpl_fullscreen_desc": "No frame or rounded corners. Traditional anamorphic full screen.",
            "tmpl_custom_name": "Custom (Free Adjustment)",
            "tmpl_custom_desc": "Customize corner radius, aspect ratio, and border margins freely.",

            "label_aspect": "Image Aspect Ratio:",
            "opt_aspect_1_1": "1:1 Square (Optimal VR - Unstretched)",
            "opt_aspect_4_3": "4:3 Balanced",
            "opt_aspect_16_9": "16:9 Widescreen",
            "opt_aspect_original": "Original Ratio",
            "opt_aspect_fill": "Stretch to Window",

            "label_fit_mode": "Window Fit Mode:",
            "opt_fit_crop": "Fill Lens (Immersive crop)",
            "opt_fit_letterbox": "Fit to Frame (100% Visible / No crop)",

            "label_content_scale": "Screen Size / FOV Scale:",
            "scale_indicator": "{val}% (Field of View)",

            "label_corner_radius": "Corner Rounding (Lens Radius):",
            "label_margin": "Outer Black Margin / Border:",
            "label_center_gap": "Interpupillary Center Gap:",

            # Live Streaming Tab
            "stream_source_title": "Live Capture Source",
            "stream_source_screen": "Full Screen (Monitors)",
            "stream_source_window": "Application Window (Browser, VLC, etc.)",
            "stream_btn_refresh_windows": "🔄 Refresh Windows",
            "stream_optical_title": "Optical Calibration & SBS Template",
            "stream_scale_label": "Scale / FOV:",
            "stream_fit_label": "Fit Mode:",
            "stream_fps_label": "Frame Rate (FPS):",
            "stream_profile_label": "Quality & Performance:",
            "stream_profile_1080p_ultra": "🌟 1080p Ultra (60 FPS / Maximum Sharpness)",
            "stream_profile_1080p_balanced": "⚖️ 1080p Balanced (30 FPS / High Quality)",
            "stream_profile_720p_fast": "⚡ 720p HD Smooth (60 FPS / Low Latency Wi-Fi)",
            "stream_profile_720p_low": "📱 720p Basic Network (30 FPS / Lower Bandwidth)",
            "stream_btn_start_projection": "🚀 Start Fullscreen Projection (F11)",
            "stream_zoom_hint": "💡 Fullscreen Shortcuts: Mouse Wheel or + / - keys to Zoom, 0 to reset.",
            "stream_web_title": "Mobile Web Server (No Cables or Apps)",
            "stream_web_switch": "Broadcast over Wi-Fi to Mobile",
            "stream_web_url_label": "Open this link in your phone's browser:",
            "stream_web_copy": "📋 Copy Link",
            "stream_web_status_off": "Web Server Stopped",
            "stream_web_status_on": "🟢 Live streaming on local network",
            "stream_help_note": "💡 Connect your phone to the same Wi-Fi as your PC, open the link in Chrome/Safari and tap 'VR Fullscreen'.",

            # Settings Tab
            "settings_general_title": "General System Settings",
            "label_export_dir": "Export Destination Folder:",
            "btn_browse": "Browse...",
            "btn_open_folder": "Open Folder",
            "label_default_crf": "Default Quality (CRF):",
            "label_language": "Interface Language:",
            "label_theme": "Visual Theme:",
            "theme_dark": "Dark Mode",
            "theme_light": "Light Mode",
            "theme_system": "System Sync",
            "btn_save_settings": "Save Settings",
            "settings_saved_msg": "Settings saved successfully to config.json!",

            # VR Info Tab
            "info_title": "How does SBS technology work for VR Shinecon?",
            "info_body": (
                "Passive VR headsets like VR Shinecon or Google Cardboard do not contain electronic "
                "screens; they use your mobile phone's display placed behind two biconvex lenses.\n\n"
                "What is Side-by-Side (SBS)?\n"
                "It is a format where a video or image is split into two horizontal halves (left and right). "
                "The left eye views the left half, and the right eye views the right half.\n\n"
                "• Half SBS (HSBS): Each picture is compressed to 50% width. When viewed through the lenses, "
                "your brain stretches them to the correct 16:9 aspect ratio. Supported by VR mobile players like "
                "VR Player, VLC VR, GizmoVR, etc.\n\n"
                "• 3D Depth Simulation (Parallax): Our application features an algorithm that introduces a controlled "
                "horizontal disparity between both images, enabling your brain to perceive realistic stereoscopic depth "
                "rather than a flat 2D image."
            ),

            # Dialogs and Errors
            "dialog_error_title": "System Error",
            "dialog_warning_title": "Warning",
            "dialog_success_title": "Operation Successful",
            "dialog_info_title": "Information",
            "ffmpeg_missing_title": "FFmpeg Not Found",
            "ffmpeg_missing_msg": (
                "FFmpeg executable was not detected on the system or PATH.\n\n"
                "FFmpeg is strictly required to convert videos to SBS format.\n"
                "Please download FFmpeg and add it to your system environment variables."
            ),
            "no_files_selected_msg": "Please import at least one video or image file to convert.",
            "conversion_finished_title": "Process Complete!",
            "conversion_finished_msg": "All files in the queue have been successfully converted.",
            "conversion_cancelled_msg": "Conversion was cancelled by the user.",
            "confirm_clear_queue": "Are you sure you want to clear the entire file queue?",
            "confirm_title": "Confirmation",
            "btn_yes": "Yes",
            "btn_no": "No",
            "btn_ok": "OK"
        }
    }

    def __init__(self, current_language: str = "es") -> None:
        """
        Inicializa el gestor de localización con el idioma especificado.
        
        Args:
            current_language (str): Código de idioma inicial ('es' o 'en').
        """
        # Idioma activo actual, por defecto español si el código no existe
        self.current_language: str = current_language if current_language in self.TRANSLATIONS else "es"
        
        # Lista de funciones callback suscritas para recibir cambios de idioma
        self._listeners: List[Callable[[str], None]] = []

    def set_language(self, language_code: str) -> None:
        """
        Cambia el idioma activo y notifica a todos los componentes de la interfaz.
        
        Args:
            language_code (str): Código del nuevo idioma ('es' o 'en').
        """
        if language_code in self.TRANSLATIONS and language_code != self.current_language:
            self.current_language = language_code
            self._notify_listeners()

    def get_language(self) -> str:
        """
        Devuelve el código del idioma activo actual.
        
        Returns:
            str: 'es' o 'en'.
        """
        return self.current_language

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Obtiene el texto traducido para una clave dada en el idioma activo.
        Permite interpolación de variables formateadas.
        
        Args:
            key (str): Identificador único del texto.
            **kwargs: Parámetros opcionales para formatear dentro de la cadena (ej. {filename}).
            
        Returns:
            str: Texto traducido y formateado. Si no existe la clave, devuelve el propio identificador.
        """
        # Obtenemos el diccionario del idioma actual
        lang_dict = self.TRANSLATIONS.get(self.current_language, self.TRANSLATIONS["es"])

        # Buscamos la traducción; si falta en el idioma actual, recurrimos al español como fallback
        text = lang_dict.get(key, self.TRANSLATIONS["es"].get(key, key))

        # Si se recibieron parámetros de formato, los interpolamos de manera segura
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError, IndexError):
                pass  # En caso de error de formateo, devolvemos la plantilla sin romper la ejecución

        return text

    def add_listener(self, callback: Callable[[str], None]) -> None:
        """
        Registra una función callback que se ejecutará cada vez que cambie el idioma.
        
        Args:
            callback (Callable[[str], None]): Función que recibe el nuevo código de idioma.
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        """
        Elimina un observador previamente registrado.
        
        Args:
            callback (Callable[[str], None]): Función a remover.
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """
        Ejecuta todas las callbacks suscritas tras un cambio de idioma.
        """
        for callback in self._listeners:
            try:
                callback(self.current_language)
            except Exception as error:
                print(f"[LocalizationManager] Error notificando a listener: {error}")
