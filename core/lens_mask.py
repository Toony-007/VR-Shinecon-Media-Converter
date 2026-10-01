# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: core/lens_mask.py
# DESCRIPCIÓN: Generador de máscaras ópticas y plantillas de formato para visores VR.
#              Permite recortar y enmarcar la imagen en formatos cuadrados (1:1),
#              4:3 o 16:9, agregando bordes perimetrales y esquinas redondeadas
#              personalizadas para evitar deformaciones por estiramiento anamórfico.
# ==============================================================================

import os
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageOps


@dataclass
class LensFormatTemplate:
    """
    Define los parámetros geométricos de una plantilla de lente o formato estereoscópico.
    """
    id: str                        # Identificador único de la plantilla
    name_key: str                  # Clave para traducción del nombre
    desc_key: str                  # Clave para traducción de la descripción
    aspect_mode: str               # Modo de aspecto: '1:1', '4:3', '16:9', 'original', 'fill'
    fit_mode: str                  # Ajuste dentro de la ventana: 'crop' (rellenar sin deformar) o 'fit' (letterbox)
    corner_radius_pct: float       # Radio de curvatura de esquinas (0.0 = rectas, 1.0 = circulares)
    margin_pct: float              # Margen perimetral negro (0.0 a 0.25)
    center_gap_pct: float          # Separación interpupilar negra central (0.0 a 0.15)


class LensMaskGenerator:
    """
    Generador de máscaras de esquinas redondeadas y compositor óptico Side-by-Side (SBS).
    Se encarga tanto de renderizar la vista previa en vivo en memoria como de generar
    el archivo PNG de máscara que FFmpeg superpone al video durante la exportación final.
    """

    # Diccionario maestro de plantillas de formato predefinidas
    PRESET_TEMPLATES: Dict[str, LensFormatTemplate] = {
        "vr_shinecon_1_1": LensFormatTemplate(
            id="vr_shinecon_1_1",
            name_key="tmpl_shinecon_1_1_name",
            desc_key="tmpl_shinecon_1_1_desc",
            aspect_mode="1:1",
            fit_mode="crop",
            corner_radius_pct=0.45,
            margin_pct=0.04,
            center_gap_pct=0.04
        ),
        "vr180_lens_mask": LensFormatTemplate(
            id="vr180_lens_mask",
            name_key="tmpl_vr180_name",
            desc_key="tmpl_vr180_desc",
            aspect_mode="1:1",
            fit_mode="crop",
            corner_radius_pct=0.75,
            margin_pct=0.03,
            center_gap_pct=0.05
        ),
        "virtual_cinema_16_9": LensFormatTemplate(
            id="virtual_cinema_16_9",
            name_key="tmpl_cinema_name",
            desc_key="tmpl_cinema_desc",
            aspect_mode="16:9",
            fit_mode="fit",
            corner_radius_pct=0.25,
            margin_pct=0.08,
            center_gap_pct=0.06
        ),
        "classic_optical_4_3": LensFormatTemplate(
            id="classic_optical_4_3",
            name_key="tmpl_4_3_name",
            desc_key="tmpl_4_3_desc",
            aspect_mode="4:3",
            fit_mode="crop",
            corner_radius_pct=0.35,
            margin_pct=0.04,
            center_gap_pct=0.04
        ),
        "half_sbs_fullscreen": LensFormatTemplate(
            id="half_sbs_fullscreen",
            name_key="tmpl_fullscreen_name",
            desc_key="tmpl_fullscreen_desc",
            aspect_mode="fill",
            fit_mode="crop",
            corner_radius_pct=0.0,
            margin_pct=0.0,
            center_gap_pct=0.0
        ),
        "custom": LensFormatTemplate(
            id="custom",
            name_key="tmpl_custom_name",
            desc_key="tmpl_custom_desc",
            aspect_mode="1:1",
            fit_mode="crop",
            corner_radius_pct=0.40,
            margin_pct=0.05,
            center_gap_pct=0.04
        )
    }

    @classmethod
    def calculate_eye_dimensions(
        cls,
        canvas_w: int,
        canvas_h: int,
        margin_pct: float,
        center_gap_pct: float
    ) -> Tuple[int, int, int, int, int, int]:
        """
        Calcula las coordenadas y tamaños rectangulares de cada ojo en la cuadrícula SBS.
        
        Args:
            canvas_w (int): Ancho total del lienzo (ej. 1920).
            canvas_h (int): Alto total del lienzo (ej. 1080).
            margin_pct (float): Porcentaje de margen perimetral.
            center_gap_pct (float): Porcentaje de separación central entre ojos.
            
        Returns:
            Tuple con (x_izq, y_izq, x_der, y_der, ancho_ojo, alto_ojo).
        """
        half_w = canvas_w // 2
        
        # Márgenes en píxeles
        mx = int(half_w * margin_pct)
        my = int(canvas_h * margin_pct)
        gap = int(half_w * center_gap_pct)

        # Dimensiones efectivas de la ventana visual de cada ojo
        eye_w = half_w - mx - (gap // 2)
        eye_h = canvas_h - (2 * my)

        # Coordenada superior izquierda para el ojo izquierdo
        x_left = mx
        y_left = my

        # Coordenada superior izquierda para el ojo derecho
        x_right = half_w + (gap // 2)
        y_right = my

        return x_left, y_left, x_right, y_right, eye_w, eye_h

    @classmethod
    def generate_mask_image(
        cls,
        width: int,
        height: int,
        corner_radius_pct: float,
        margin_pct: float,
        center_gap_pct: float
    ) -> Image.Image:
        """
        Genera una imagen RGBA negra con dos cortes transparentes y esquinas redondeadas
        para los ojos izquierdo y derecho.
        
        Args:
            width (int): Ancho total.
            height (int): Alto total.
            corner_radius_pct (float): 0.0 a 1.0 (proporción del radio respecto al menor lado).
            margin_pct (float): Margen exterior.
            center_gap_pct (float): Separación central.
            
        Returns:
            PIL.Image.Image: Máscara en modo RGBA.
        """
        # Lienzo opaco completamente negro
        mask = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(mask)

        # Calculamos la geometría de los ojos
        x_l, y_l, x_r, y_r, eye_w, eye_h = cls.calculate_eye_dimensions(
            width, height, margin_pct, center_gap_pct
        )

        # Calculamos el radio en píxeles (limitado al 50% de la menor dimensión para no deformar)
        max_possible_r = min(eye_w, eye_h) // 2
        radius_px = int(max_possible_r * max(0.0, min(corner_radius_pct, 1.0)))

        # Dibujamos corte transparente (0, 0, 0, 0) para el ojo izquierdo
        left_box = [x_l, y_l, x_l + eye_w, y_l + eye_h]
        if radius_px > 0:
            draw.rounded_rectangle(left_box, radius=radius_px, fill=(0, 0, 0, 0))
        else:
            draw.rectangle(left_box, fill=(0, 0, 0, 0))

        # Dibujamos corte transparente para el ojo derecho
        right_box = [x_r, y_r, x_r + eye_w, y_r + eye_h]
        if radius_px > 0:
            draw.rounded_rectangle(right_box, radius=radius_px, fill=(0, 0, 0, 0))
        else:
            draw.rectangle(right_box, fill=(0, 0, 0, 0))

        return mask

    @classmethod
    def fit_source_frame(
        cls,
        frame: Image.Image,
        target_w: int,
        target_h: int,
        aspect_mode: str,
        fit_mode: str
    ) -> Image.Image:
        """
        Adapta el fotograma original a las proporciones deseadas (1:1, 4:3, 16:9, etc.)
        evitando el estiramiento horizontal no deseado.
        
        Args:
            frame (PIL.Image): Fotograma original.
            target_w (int): Ancho deseado de la ventana del ojo.
            target_h (int): Alto deseado de la ventana del ojo.
            aspect_mode (str): '1:1', '4:3', '16:9', 'original', 'fill'.
            fit_mode (str): 'crop' (recortar bordes sobrantes) o 'fit' (añadir barras negras).
            
        Returns:
            PIL.Image.Image: Fotograma transformado con dimensiones exactas (target_w, target_h).
        """
        # Determinamos la relación de aspecto numérica objetivo
        if aspect_mode == "1:1":
            target_ratio = 1.0
        elif aspect_mode == "4:3":
            target_ratio = 4.0 / 3.0
        elif aspect_mode == "16:9":
            target_ratio = 16.0 / 9.0
        elif aspect_mode == "original":
            target_ratio = frame.width / frame.height if frame.height > 0 else (16.0 / 9.0)
        else:
            # Modo fill / estirar a la ventana
            return frame.resize((target_w, target_h), Image.Resampling.BILINEAR)

        # Calculamos dimensiones del área de contenido según el ratio
        window_ratio = target_w / target_h if target_h > 0 else 1.0

        if fit_mode == "crop":
            # Recorte centrado (Center Crop) preservando el aspecto objetivo
            content_img = ImageOps.fit(frame, (target_w, target_h), centering=(0.5, 0.5))
            return content_img
        else:
            # Modo 'fit' con barras negras (Letterbox / Pillarbox)
            if target_ratio >= window_ratio:
                # Limitado por ancho
                content_w = target_w
                content_h = int(target_w / target_ratio)
            else:
                # Limitado por alto
                content_h = target_h
                content_w = int(target_h * target_ratio)

            resized = frame.resize((max(1, content_w), max(1, content_h)), Image.Resampling.BILINEAR)
            padded = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            offset_x = (target_w - content_w) // 2
            offset_y = (target_h - content_h) // 2
            padded.paste(resized, (offset_x, offset_y))
            return padded

    @classmethod
    def compose_preview_sbs(
        cls,
        source_frame: Image.Image,
        target_canvas_w: int = 1920,
        target_canvas_h: int = 1080,
        aspect_mode: str = "1:1",
        fit_mode: str = "crop",
        corner_radius_pct: float = 0.45,
        margin_pct: float = 0.04,
        center_gap_pct: float = 0.04,
        parallax_px: int = 0
    ) -> Image.Image:
        """
        Compone la imagen final Side-by-Side estereoscópica completa para la vista previa
        o procesamiento en vivo, aplicando la máscara de esquinas y disparidad 3D.
        
        Args:
            source_frame (PIL.Image): Fotograma original capturado.
            target_canvas_w (int): Ancho total de salida (ej. 1920).
            target_canvas_h (int): Alto total de salida (ej. 1080).
            aspect_mode (str): Proporción ('1:1', '4:3', '16:9', etc.).
            fit_mode (str): 'crop' o 'fit'.
            corner_radius_pct (float): Porcentaje de radio de curvatura de esquinas.
            margin_pct (float): Margen exterior negro.
            center_gap_pct (float): Espaciador central.
            parallax_px (int): Píxeles de desplazamiento estereoscópico 3D.
            
        Returns:
            PIL.Image.Image: Imagen final SBS lista para mostrar o guardar.
        """
        # Lienzo base negro para la salida final
        canvas = Image.new("RGBA", (target_canvas_w, target_canvas_h), (0, 0, 0, 255))

        # Obtenemos geometría de ambos ojos
        x_l, y_l, x_r, y_r, eye_w, eye_h = cls.calculate_eye_dimensions(
            target_canvas_w, target_canvas_h, margin_pct, center_gap_pct
        )

        # Ajustamos el fotograma fuente al tamaño de la ventana
        fitted_frame = cls.fit_source_frame(source_frame, eye_w, eye_h, aspect_mode, fit_mode)

        # Simulación de disparidad 3D Parallax si es mayor a 0
        if parallax_px > 0:
            p = min(parallax_px, 50)
            # Ojo izquierdo recortado con desplazamiento positivo
            left_cropped = fitted_frame.crop((p, 0, eye_w, eye_h)).resize((eye_w, eye_h), Image.Resampling.BILINEAR)
            # Ojo derecho recortado con desplazamiento opuesto
            right_cropped = fitted_frame.crop((0, 0, eye_w - p, eye_h)).resize((eye_w, eye_h), Image.Resampling.BILINEAR)
            eye_left_img = left_cropped
            eye_right_img = right_cropped
        else:
            eye_left_img = fitted_frame
            eye_right_img = fitted_frame

        # Pegamos el contenido en las posiciones de los ojos
        canvas.paste(eye_left_img, (x_l, y_l))
        canvas.paste(eye_right_img, (x_r, y_r))

        # Si hay esquinas redondeadas o márgenes, superponemos la máscara óptica
        if corner_radius_pct > 0 or margin_pct > 0 or center_gap_pct > 0:
            mask = cls.generate_mask_image(
                target_canvas_w, target_canvas_h, corner_radius_pct, margin_pct, center_gap_pct
            )
            # Combinamos la máscara alfa sobre el lienzo
            canvas = Image.alpha_composite(canvas, mask)

        # Convertimos a formato RGB final
        return canvas.convert("RGB")
