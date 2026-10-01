# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/tab_conversion.py
# DESCRIPCIÓN: Pestaña principal de conversión multimedia con soporte para
#              plantillas ópticas, esquinas redondeadas, bordes perimetrales,
#              vista previa en vivo interactiva y procesamiento concurrente.
# ==============================================================================

import os
import time
import threading
import tkinter.filedialog as filedialog
import customtkinter as ctk
from typing import List, Optional, Any
from PIL import Image

from config.config_manager import ConfigManager
from core.localization import LocalizationManager
from core.lens_mask import LensMaskGenerator, LensFormatTemplate
from core.media_processor import MediaProcessor, MediaItem, ConversionOptions
from ui.dialogs import ModernMessageDialog, ModernConfirmDialog, ModernPreviewModal


class ConversionTab(ctk.CTkFrame):
    """
    Vista principal de conversión estereoscópica Side-by-Side (SBS).
    Integra la cola de procesamiento, plantillas de ajuste de esquinas y bordes,
    un visor de previsualización en vivo en tiempo real y la consola de logs.
    """

    def __init__(
        self,
        parent: Any,
        config_mgr: ConfigManager,
        loc_mgr: LocalizationManager,
        processor: MediaProcessor
    ) -> None:
        """
        Inicializa la pestaña de conversión.
        
        Args:
            parent (Any): Contenedor visual padre.
            config_mgr (ConfigManager): Gestor de persistencia.
            loc_mgr (LocalizationManager): Gestor de idiomas.
            processor (MediaProcessor): Motor FFmpeg.
        """
        super().__init__(parent, fg_color="transparent")

        self.config_mgr = config_mgr
        self.loc_mgr = loc_mgr
        self.processor = processor

        # Cola de archivos multimedia
        self.queue_items: List[MediaItem] = []
        self.item_widgets: dict = {}

        # Archivo actualmente seleccionado para la vista previa
        self.selected_preview_item: Optional[MediaItem] = None
        
        # Caché del fotograma base extraído para previsualización a 60 FPS
        self._cached_source_frame: Optional[Image.Image] = None
        self._cached_source_path: str = ""
        self._last_composed_preview: Optional[Image.Image] = None

        # Control de estado de transcodificación
        self.is_converting: bool = False

        # Suscripción al gestor de localización
        self.loc_mgr.add_listener(self._update_ui_texts)

        # Construcción visual de la interfaz
        self._build_ui()

    def _build_ui(self) -> None:
        """
        Crea los elementos gráficos y distribuye los pesos de la cuadrícula (Grid).
        """
        # Sistema de columnas: Columna 0 (Cola y Opciones, peso 1), Columna 1 (Vista Previa, Progreso y Log, peso 1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ======================================================================
        # PANEL IZQUIERDO: IMPORTACIÓN, COLA, PLANTILLAS Y PARÁMETROS
        # ======================================================================
        self.left_panel = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------------------------
        # TARJETA 1: BOTONES DE IMPORTACIÓN Y COLA DE MEDIOS
        # ----------------------------------------------------------------------
        self.import_card = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.import_card.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.import_card.grid_columnconfigure(0, weight=1)

        import_buttons_frame = ctk.CTkFrame(self.import_card, fg_color="transparent")
        import_buttons_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=12)
        import_buttons_frame.grid_columnconfigure(0, weight=3)
        import_buttons_frame.grid_columnconfigure(1, weight=1)

        self.btn_import = ctk.CTkButton(
            import_buttons_frame,
            text=f"📂  {self.loc_mgr.t('import_files')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            command=self._on_import_files
        )
        self.btn_import.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_clear = ctk.CTkButton(
            import_buttons_frame,
            text=self.loc_mgr.t("clear_queue"),
            font=ctk.CTkFont(size=12),
            height=42,
            fg_color="#475569",
            hover_color="#334155",
            command=self._on_clear_queue
        )
        self.btn_clear.grid(row=0, column=1, sticky="ew")

        # Cabecera de la cola
        self.lbl_queue_title = ctk.CTkLabel(
            self.left_panel,
            text=self.loc_mgr.t("queue_title"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_queue_title.grid(row=1, column=0, sticky="w", padx=10, pady=(10, 4))

        self.queue_frame = ctk.CTkFrame(self.left_panel, corner_radius=10, height=160)
        self.queue_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.queue_frame.grid_columnconfigure(0, weight=1)

        self.lbl_empty_queue = ctk.CTkLabel(
            self.queue_frame,
            text=self.loc_mgr.t("no_files_queued"),
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#94a3b8"
        )
        self.lbl_empty_queue.pack(padx=20, pady=35)

        self.items_container = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        self.items_container.pack(fill="both", expand=True, padx=5, pady=5)

        # ----------------------------------------------------------------------
        # TARJETA 2: PLANTILLAS DE FORMATO Y ESQUINAS REDONDEADAS
        # ----------------------------------------------------------------------
        self.template_card = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.template_card.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        self.template_card.grid_columnconfigure((0, 1), weight=1)

        self.lbl_tmpl_title = ctk.CTkLabel(
            self.template_card,
            text=f"🎯 {self.loc_mgr.t('label_template')}",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_tmpl_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 4))

        # Menú desplegable de plantillas predefinidas
        self.template_keys = [
            "virtual_cinema_full",
            "vr_shinecon_1_1",
            "vr180_lens_mask",
            "virtual_cinema_16_9",
            "classic_optical_4_3",
            "half_sbs_fullscreen",
            "custom"
        ]
        self.template_names = [self.loc_mgr.t(LensMaskGenerator.PRESET_TEMPLATES[k].name_key) for k in self.template_keys]

        self.opt_template = ctk.CTkOptionMenu(
            self.template_card,
            values=self.template_names,
            command=self._on_template_selected,
            height=34
        )
        self.opt_template.set(self.template_names[0])
        self.opt_template.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 6))

        # Descripción dinámica de la plantilla activa
        self.lbl_tmpl_desc = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t(LensMaskGenerator.PRESET_TEMPLATES["virtual_cinema_full"].desc_key),
            wraplength=440,
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_tmpl_desc.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 10))

        # Control 1: Curvatura de Esquinas (Radio Lente)
        self.lbl_corner_radius = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_corner_radius"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_corner_radius.grid(row=3, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_corner_indicator = ctk.CTkLabel(
            self.template_card,
            text="45% (Curvatura Lente VR Shinecon)",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_corner_indicator.grid(row=4, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_corner_radius = ctk.CTkSlider(
            self.template_card,
            from_=0.0,
            to=1.0,
            number_of_steps=20,
            command=self._on_corner_slider_changed
        )
        self.slider_corner_radius.set(0.45)
        self.slider_corner_radius.grid(row=5, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))

        # Control 2: Margen / Borde Negro Exterior
        self.lbl_margin = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_margin"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_margin.grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_margin_indicator = ctk.CTkLabel(
            self.template_card,
            text="4% (Borde Protector de Lente)",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_margin_indicator.grid(row=7, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_margin = ctk.CTkSlider(
            self.template_card,
            from_=0.0,
            to=0.20,
            number_of_steps=20,
            command=self._on_margin_slider_changed
        )
        self.slider_margin.set(0.04)
        self.slider_margin.grid(row=8, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))

        # Control 3: Relación de Aspecto
        self.lbl_aspect = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_aspect"),
            font=ctk.CTkFont(size=12)
        )
        self.lbl_aspect.grid(row=9, column=0, sticky="w", padx=15, pady=(4, 2))

        self.opt_aspect = ctk.CTkOptionMenu(
            self.template_card,
            values=[
                self.loc_mgr.t("opt_aspect_1_1"),
                self.loc_mgr.t("opt_aspect_4_3"),
                self.loc_mgr.t("opt_aspect_16_9"),
                self.loc_mgr.t("opt_aspect_original"),
                self.loc_mgr.t("opt_aspect_fill")
            ],
            command=lambda _: self._on_params_changed()
        )
        self.opt_aspect.set(self.loc_mgr.t("opt_aspect_1_1"))
        self.opt_aspect.grid(row=10, column=0, sticky="ew", padx=(15, 6), pady=(0, 10))

        # Control 4: Modo de Ajuste en Ventana (Crop vs Letterbox)
        self.lbl_fit = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_fit_mode"),
            font=ctk.CTkFont(size=12)
        )
        self.lbl_fit.grid(row=9, column=1, sticky="w", padx=6, pady=(4, 2))

        self.opt_fit = ctk.CTkOptionMenu(
            self.template_card,
            values=[self.loc_mgr.t("opt_fit_crop"), self.loc_mgr.t("opt_fit_letterbox")],
            command=lambda _: self._on_params_changed()
        )
        self.opt_fit.set(self.loc_mgr.t("opt_fit_crop"))
        self.opt_fit.grid(row=10, column=1, sticky="ew", padx=(6, 15), pady=(0, 10))

        # Control 5: Separación Central Interpupilar (IPD)
        self.lbl_center_gap = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_center_gap"),
            font=ctk.CTkFont(size=12)
        )
        self.lbl_center_gap.grid(row=11, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_gap_indicator = ctk.CTkLabel(
            self.template_card,
            text="4% (Separación Central Interpupilar)",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_gap_indicator.grid(row=12, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_center_gap = ctk.CTkSlider(
            self.template_card,
            from_=0.0,
            to=0.15,
            number_of_steps=15,
            command=self._on_gap_slider_changed
        )
        self.slider_center_gap.set(0.04)
        self.slider_center_gap.grid(row=13, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))

        # Control 6: Escala de Campo de Visión (FOV / Zoom de Pantalla)
        self.lbl_scale = ctk.CTkLabel(
            self.template_card,
            text=self.loc_mgr.t("label_content_scale"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_scale.grid(row=14, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_scale_indicator = ctk.CTkLabel(
            self.template_card,
            text="95% (Pantalla Alejada / 100% Contenido Visible)",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_scale_indicator.grid(row=15, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_content_scale = ctk.CTkSlider(
            self.template_card,
            from_=0.50,
            to=1.50,
            number_of_steps=20,
            command=self._on_scale_slider_changed
        )
        self.slider_content_scale.set(0.95)
        self.slider_content_scale.grid(row=16, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        # ----------------------------------------------------------------------
        # TARJETA 3: OPCIONES TÉCNICAS (RESOLUCIÓN, CÓDEC, CRF, PARALLAX)
        # ----------------------------------------------------------------------
        self.advanced_card = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.advanced_card.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        self.advanced_card.grid_columnconfigure((0, 1), weight=1)

        self.lbl_adv_title = ctk.CTkLabel(
            self.advanced_card,
            text=f"⚙️ {self.loc_mgr.t('advanced_options_title')}",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_adv_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 6))

        # Resolución y Contenedor
        self.lbl_res = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_resolution"), font=ctk.CTkFont(size=12))
        self.lbl_res.grid(row=1, column=0, sticky="w", padx=15, pady=(4, 2))
        self.opt_res = ctk.CTkOptionMenu(
            self.advanced_card,
            values=[
                self.loc_mgr.t("opt_res_1080p"),
                self.loc_mgr.t("opt_res_720p"),
                self.loc_mgr.t("opt_res_1440p"),
                self.loc_mgr.t("opt_res_4k"),
                self.loc_mgr.t("opt_res_original")
            ]
        )
        self.opt_res.grid(row=2, column=0, sticky="ew", padx=(15, 6), pady=(0, 8))

        self.lbl_container = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_container"), font=ctk.CTkFont(size=12))
        self.lbl_container.grid(row=1, column=1, sticky="w", padx=6, pady=(4, 2))
        self.opt_container = ctk.CTkOptionMenu(self.advanced_card, values=["MP4 (.mp4)", "MKV (.mkv)"])
        self.opt_container.grid(row=2, column=1, sticky="ew", padx=(6, 15), pady=(0, 8))

        # Aceleración GPU y Calidad CRF
        self.lbl_enc = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_encoder"), font=ctk.CTkFont(size=12))
        self.lbl_enc.grid(row=3, column=0, sticky="w", padx=15, pady=(4, 2))
        self.opt_encoder = ctk.CTkOptionMenu(
            self.advanced_card,
            values=[
                self.loc_mgr.t("opt_enc_cpu"),
                self.loc_mgr.t("opt_enc_nvenc"),
                self.loc_mgr.t("opt_enc_qsv"),
                self.loc_mgr.t("opt_enc_amf")
            ]
        )
        self.opt_encoder.grid(row=4, column=0, sticky="ew", padx=(15, 6), pady=(0, 8))

        self.lbl_audio = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_audio"), font=ctk.CTkFont(size=12))
        self.lbl_audio.grid(row=3, column=1, sticky="w", padx=6, pady=(4, 2))
        self.opt_audio = ctk.CTkOptionMenu(
            self.advanced_card,
            values=[self.loc_mgr.t("opt_audio_copy"), self.loc_mgr.t("opt_audio_aac")]
        )
        self.opt_audio.grid(row=4, column=1, sticky="ew", padx=(6, 15), pady=(0, 8))

        # Calidad CRF Slider
        self.lbl_crf_title = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_quality"), font=ctk.CTkFont(size=12))
        self.lbl_crf_title.grid(row=5, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_crf_indicator = ctk.CTkLabel(self.advanced_card, text="CRF: 18 - Alta Nitidez (Óptimo VR)", font=ctk.CTkFont(size=11))
        self.lbl_crf_indicator.grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_crf = ctk.CTkSlider(self.advanced_card, from_=14, to=28, number_of_steps=14, command=self._on_crf_slider_move)
        self.slider_crf.set(18)
        self.slider_crf.grid(row=7, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))

        # Efecto 3D Parallax Slider
        self.lbl_parallax = ctk.CTkLabel(self.advanced_card, text=self.loc_mgr.t("label_parallax"), font=ctk.CTkFont(size=12))
        self.lbl_parallax.grid(row=8, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 2))

        self.lbl_parallax_indicator = ctk.CTkLabel(self.advanced_card, text="0 px (2D Plano Duplicado)", font=ctk.CTkFont(size=11))
        self.lbl_parallax_indicator.grid(row=9, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 2))

        self.slider_parallax = ctk.CTkSlider(self.advanced_card, from_=0, to=30, number_of_steps=15, command=self._on_parallax_slider_move)
        self.slider_parallax.set(0)
        self.slider_parallax.grid(row=10, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        # ======================================================================
        # PANEL DERECHO: VISTA PREVIA EN VIVO, ACCIONES, PROGRESO Y LOGS
        # ======================================================================
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(3, weight=1)

        # ----------------------------------------------------------------------
        # TARJETA 4: VISTA PREVIA EN VIVO ESTEREOSCÓPICA
        # ----------------------------------------------------------------------
        self.preview_card = ctk.CTkFrame(self.right_panel, corner_radius=10)
        self.preview_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.preview_card.grid_columnconfigure(0, weight=1)

        preview_header_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        preview_header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        preview_header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_preview_title = ctk.CTkLabel(
            preview_header_frame,
            text=f"👓 {self.loc_mgr.t('preview_title')}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_preview_title.grid(row=0, column=0, sticky="w")

        # Botones de la barra de vista previa
        btn_preview_tools = ctk.CTkFrame(preview_header_frame, fg_color="transparent")
        btn_preview_tools.grid(row=0, column=1, sticky="e")

        self.btn_refresh_prev = ctk.CTkButton(
            btn_preview_tools,
            text=self.loc_mgr.t("btn_refresh_preview"),
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_refresh_preview_clicked
        )
        self.btn_refresh_prev.pack(side="left", padx=(0, 6))

        self.btn_enlarge = ctk.CTkButton(
            btn_preview_tools,
            text=self.loc_mgr.t("btn_enlarge_preview"),
            width=120,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._on_enlarge_preview
        )
        self.btn_enlarge.pack(side="left")

        # Lienzo visual para mostrar el fotograma previsualizado
        self.preview_box = ctk.CTkFrame(self.preview_card, fg_color="#000000", corner_radius=8, height=220)
        self.preview_box.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self.preview_box.grid_propagate(False)
        self.preview_box.grid_columnconfigure(0, weight=1)
        self.preview_box.grid_rowconfigure(0, weight=1)

        self.lbl_preview_canvas = ctk.CTkLabel(
            self.preview_box,
            text=self.loc_mgr.t("preview_no_file"),
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#64748b"
        )
        self.lbl_preview_canvas.grid(row=0, column=0, sticky="nsew")

        # Pie informativo de la vista previa
        self.lbl_preview_footer = ctk.CTkLabel(
            self.preview_card,
            text="Esquinas y óptica calibradas para lentes pasivas VR Shinecon",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8"
        )
        self.lbl_preview_footer.grid(row=2, column=0, sticky="w", padx=14, pady=(2, 8))

        # ----------------------------------------------------------------------
        # TARJETA 5: ACCIONES DE EJECUCIÓN (INICIAR / CANCELAR)
        # ----------------------------------------------------------------------
        actions_frame = ctk.CTkFrame(self.right_panel, corner_radius=10)
        actions_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        actions_frame.grid_columnconfigure(0, weight=3)
        actions_frame.grid_columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(
            actions_frame,
            text=f"▶  {self.loc_mgr.t('btn_start_conversion')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self._on_start_conversion
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=12)

        self.btn_cancel = ctk.CTkButton(
            actions_frame,
            text=f"⏹ {self.loc_mgr.t('btn_cancel_conversion')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=44,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            state="disabled",
            command=self._on_cancel_conversion
        )
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(6, 12), pady=12)

        # ----------------------------------------------------------------------
        # TARJETA 6: PROGRESO DE TRANSCODIFICACIÓN
        # ----------------------------------------------------------------------
        progress_card = ctk.CTkFrame(self.right_panel, corner_radius=10)
        progress_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        progress_card.grid_columnconfigure(0, weight=1)

        self.lbl_progress_file = ctk.CTkLabel(
            progress_card,
            text=self.loc_mgr.t("progress_title"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_progress_file.grid(row=0, column=0, sticky="w", padx=15, pady=(8, 2))

        self.progress_bar_file = ctk.CTkProgressBar(progress_card, height=10)
        self.progress_bar_file.set(0.0)
        self.progress_bar_file.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 2))

        self.lbl_progress_details = ctk.CTkLabel(
            progress_card,
            text="0% | Esperando inicio...",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_progress_details.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 6))

        self.lbl_progress_overall = ctk.CTkLabel(
            progress_card,
            text=self.loc_mgr.t("progress_overall"),
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_progress_overall.grid(row=3, column=0, sticky="w", padx=15, pady=(2, 2))

        self.progress_bar_overall = ctk.CTkProgressBar(progress_card, height=8)
        self.progress_bar_overall.set(0.0)
        self.progress_bar_overall.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 2))

        self.lbl_overall_details = ctk.CTkLabel(
            progress_card,
            text="0 / 0 completados",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_overall_details.grid(row=5, column=0, sticky="w", padx=15, pady=(0, 10))

        # ----------------------------------------------------------------------
        # TARJETA 7: CONSOLA DE REGISTROS (LOGS)
        # ----------------------------------------------------------------------
        console_card = ctk.CTkFrame(self.right_panel, corner_radius=10)
        console_card.grid(row=3, column=0, sticky="nsew")
        console_card.grid_columnconfigure(0, weight=1)
        console_card.grid_rowconfigure(1, weight=1)

        self.lbl_console_title = ctk.CTkLabel(
            console_card,
            text=self.loc_mgr.t("console_title"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_console_title.grid(row=0, column=0, sticky="w", padx=15, pady=(8, 2))

        self.txt_console = ctk.CTkTextbox(
            console_card,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
            state="disabled"
        )
        self.txt_console.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.append_log(self.loc_mgr.t("log_ready"))

    def append_log(self, text: str) -> None:
        """
        Agrega un mensaje con marca temporal a la consola de registro de manera thread-safe.
        """
        def _insert() -> None:
            now_str = time.strftime("[%H:%M:%S] ")
            self.txt_console.configure(state="normal")
            self.txt_console.insert("end", now_str + text + "\n")
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")

        self.after(0, _insert)

    def _on_import_files(self) -> None:
        """
        Abre el explorador de archivos para importar videos e imágenes a la cola.
        """
        file_types = [
            ("Archivos Multimedia", "*.mp4 *.mkv *.avi *.mov *.flv *.webm *.jpg *.jpeg *.png *.webp *.bmp"),
            ("Videos", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"),
            ("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"),
            ("Todos los archivos", "*.*")
        ]

        selected_paths = filedialog.askopenfilenames(
            title=self.loc_mgr.t("import_files"),
            filetypes=file_types
        )

        if not selected_paths:
            return

        added_count = 0
        for path in selected_paths:
            if not self.processor.is_supported_file(path):
                self.append_log(f"[AVISO] Archivo no compatible omitido: {os.path.basename(path)}")
                continue

            if any(item.file_path == path for item in self.queue_items):
                continue

            media_item = self.processor.inspect_file(path)
            self.queue_items.append(media_item)
            added_count += 1

        if added_count > 0:
            self._render_queue_items()
            self.append_log(f"Se añadieron {added_count} archivo(s) a la cola de conversión.")
            self._update_overall_progress_labels()

            # Si no hay archivo de previsualización activo, seleccionamos el primero
            if self.selected_preview_item is None and self.queue_items:
                self.selected_preview_item = self.queue_items[0]
                self._load_source_frame_and_update_preview()

    def _render_queue_items(self) -> None:
        """
        Reconstruye visualmente la lista de archivos en cola.
        """
        for widget in self.items_container.winfo_children():
            widget.destroy()
        self.item_widgets.clear()

        if not self.queue_items:
            self.lbl_empty_queue.pack(padx=20, pady=35)
            self.selected_preview_item = None
            self._cached_source_frame = None
            self._cached_source_path = ""
            self.lbl_preview_canvas.configure(image="", text=self.loc_mgr.t("preview_no_file"))
            return

        self.lbl_empty_queue.pack_forget()

        for item in self.queue_items:
            is_active = (self.selected_preview_item and self.selected_preview_item.file_path == item.file_path)
            row_bg = ("#cbd5e1", "#1e293b") if is_active else ("#f1f5f9", "#0f172a")

            item_row = ctk.CTkFrame(self.items_container, fg_color=row_bg, corner_radius=6)
            item_row.pack(fill="x", padx=4, pady=3)
            item_row.grid_columnconfigure(0, weight=1)

            type_icon = "🎬" if item.media_type == "video" else "🖼️"
            info_text = f"{type_icon} {item.file_name}  ({item.width}x{item.height} | {item.duration_formatted} | {item.file_size_formatted})"

            lbl_name = ctk.CTkLabel(
                item_row,
                text=info_text,
                font=ctk.CTkFont(size=11, weight="bold" if is_active else "normal"),
                anchor="w"
            )
            lbl_name.grid(row=0, column=0, sticky="w", padx=10, pady=4)

            # Click en la fila para previsualizar este archivo específico
            lbl_name.bind("<Button-1>", lambda e, it=item: self._select_preview_item(it))
            item_row.bind("<Button-1>", lambda e, it=item: self._select_preview_item(it))

            status_colors = {
                "pending": ("#64748b", self.loc_mgr.t("status_pending")),
                "processing": ("#0284c7", self.loc_mgr.t("status_processing")),
                "completed": ("#16a34a", self.loc_mgr.t("status_completed")),
                "error": ("#dc2626", self.loc_mgr.t("status_error")),
                "cancelled": ("#d97706", self.loc_mgr.t("status_cancelled"))
            }
            bg_c, text_status = status_colors.get(item.status, ("#64748b", item.status))

            lbl_status = ctk.CTkLabel(
                item_row,
                text=f" {text_status} ",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#ffffff",
                fg_color=bg_c,
                corner_radius=4
            )
            lbl_status.grid(row=0, column=1, padx=6, pady=4)

            btn_remove = ctk.CTkButton(
                item_row,
                text="✕",
                width=24,
                height=24,
                fg_color="transparent",
                text_color="#ef4444",
                hover_color=("#e2e8f0", "#1e293b"),
                command=lambda it=item: self._on_remove_item(it)
            )
            btn_remove.grid(row=0, column=2, padx=(0, 6), pady=4)

            self.item_widgets[item.file_path] = {
                "row": item_row,
                "status_lbl": lbl_status,
                "remove_btn": btn_remove
            }

    def _select_preview_item(self, item: MediaItem) -> None:
        """
        Selecciona un archivo de la lista y actualiza inmediatamente la vista previa en vivo.
        """
        self.selected_preview_item = item
        self._render_queue_items()
        self._load_source_frame_and_update_preview()

    def _on_remove_item(self, item: MediaItem) -> None:
        """
        Elimina un archivo de la cola.
        """
        if self.is_converting and item.status == "processing":
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_warning_title"),
                "No puedes remover un archivo que está siendo transcodificado en este instante.",
                "warning"
            )
            return

        if item in self.queue_items:
            self.queue_items.remove(item)
            if self.selected_preview_item == item:
                self.selected_preview_item = self.queue_items[0] if self.queue_items else None
            self._render_queue_items()
            self._update_overall_progress_labels()
            self._load_source_frame_and_update_preview()

    def _on_clear_queue(self) -> None:
        """
        Vacia la cola completa previa confirmación.
        """
        if self.is_converting:
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_warning_title"),
                "No es posible limpiar la lista mientras hay una conversión en curso.",
                "warning"
            )
            return

        if not self.queue_items:
            return

        confirm = ModernConfirmDialog(
            self.winfo_toplevel(),
            self.loc_mgr.t("confirm_title"),
            self.loc_mgr.t("confirm_clear_queue"),
            self.loc_mgr.t("btn_yes"),
            self.loc_mgr.t("btn_no")
        )
        if confirm.result:
            self.queue_items.clear()
            self.selected_preview_item = None
            self._cached_source_frame = None
            self._cached_source_path = ""
            self._render_queue_items()
            self._update_overall_progress_labels()
            self.append_log("La cola de archivos ha sido vaciada.")

    # --------------------------------------------------------------------------
    # GESTIÓN DE PLANTILLAS Y CONTROL DE ESQUINAS REDONDEADAS
    # --------------------------------------------------------------------------
    def _on_template_selected(self, choice: str) -> None:
        """
        Aplica los parámetros geométricos de la plantilla seleccionada y refresca la vista previa.
        """
        # Identificamos la clave de la plantilla seleccionada
        chosen_id = "vr_shinecon_1_1"
        for k in self.template_keys:
            if self.loc_mgr.t(LensMaskGenerator.PRESET_TEMPLATES[k].name_key) == choice:
                chosen_id = k
                break

        tmpl = LensMaskGenerator.PRESET_TEMPLATES[chosen_id]
        self.lbl_tmpl_desc.configure(text=self.loc_mgr.t(tmpl.desc_key))

        # Si no es personalizado, actualizamos los controles a los valores de la plantilla
        if chosen_id != "custom":
            self.slider_corner_radius.set(tmpl.corner_radius_pct)
            self._on_corner_slider_changed(tmpl.corner_radius_pct, trigger_preview=False)

            self.slider_margin.set(tmpl.margin_pct)
            self._on_margin_slider_changed(tmpl.margin_pct, trigger_preview=False)

            self.slider_center_gap.set(tmpl.center_gap_pct)
            self._on_gap_slider_changed(tmpl.center_gap_pct, trigger_preview=False)

            # Ajuste de aspecto
            aspect_map = {
                "1:1": self.loc_mgr.t("opt_aspect_1_1"),
                "4:3": self.loc_mgr.t("opt_aspect_4_3"),
                "16:9": self.loc_mgr.t("opt_aspect_16_9"),
                "original": self.loc_mgr.t("opt_aspect_original"),
                "fill": self.loc_mgr.t("opt_aspect_fill")
            }
            self.opt_aspect.set(aspect_map.get(tmpl.aspect_mode, self.loc_mgr.t("opt_aspect_1_1")))

            # Modo de encaje
            fit_text = self.loc_mgr.t("opt_fit_crop") if tmpl.fit_mode == "crop" else self.loc_mgr.t("opt_fit_letterbox")
            self.opt_fit.set(fit_text)

            # Escala FOV
            scale_val = getattr(tmpl, "content_scale", 1.0)
            self.slider_content_scale.set(scale_val)
            self._on_scale_slider_changed(scale_val, trigger_preview=False)

        self._on_params_changed()

    def _on_scale_slider_changed(self, value: float, trigger_preview: bool = True) -> None:
        """
        Maneja cambios en el slider de escala de campo de visión (FOV / Zoom).
        """
        pct = int(round(value * 100))
        if pct == 100:
            desc = "100% (Tamaño de Ventana Estándar)"
        elif pct < 100:
            desc = f"{pct}% (Pantalla Alejada / 100% Contenido Visible)"
        else:
            desc = f"{pct}% (Zoom / Acercamiento Inmersivo)"

        self.lbl_scale_indicator.configure(text=desc)
        if trigger_preview:
            self._on_params_changed()

    def _on_corner_slider_changed(self, value: float, trigger_preview: bool = True) -> None:
        """
        Maneja cambios en el slider de radio de curvatura de esquinas.
        """
        pct = int(value * 100)
        if pct == 0:
            desc = "0% (Esquinas Rectas / Sin Máscara)"
        elif pct <= 30:
            desc = f"{pct}% (Curvatura Suave)"
        elif pct <= 60:
            desc = f"{pct}% (Curvatura Óptima VR Shinecon)"
        else:
            desc = f"{pct}% (Máscara Barril Profunda / VR180)"

        self.lbl_corner_indicator.configure(text=desc)
        if trigger_preview:
            self._on_params_changed()

    def _on_margin_slider_changed(self, value: float, trigger_preview: bool = True) -> None:
        """
        Maneja cambios en el slider de margen perimetral.
        """
        pct = int(value * 100)
        self.lbl_margin_indicator.configure(text=f"{pct}% (Borde Negro Perimetral)")
        if trigger_preview:
            self._on_params_changed()

    def _on_gap_slider_changed(self, value: float, trigger_preview: bool = True) -> None:
        """
        Maneja cambios en el slider de separación central.
        """
        pct = int(value * 100)
        self.lbl_gap_indicator.configure(text=f"{pct}% (Separación Central Interpupilar)")
        if trigger_preview:
            self._on_params_changed()

    def _on_crf_slider_move(self, value: float) -> None:
        """
        Actualiza la etiqueta informativa de calidad al deslizar el control CRF.
        """
        crf_int = int(round(value))
        if crf_int <= 17:
            desc = "Calidad Extrema (Archivo pesado)"
        elif crf_int <= 20:
            desc = "Alta Nitidez (Óptimo VR)"
        elif crf_int <= 23:
            desc = "Equilibrado Estándar"
        else:
            desc = "Mayor Compresión"
        self.lbl_crf_indicator.configure(text=f"CRF: {crf_int} - {desc}")

    def _on_parallax_slider_move(self, value: float) -> None:
        """
        Actualiza la etiqueta descriptiva del efecto 3D Parallax y refresca el visor.
        """
        val_int = int(round(value))
        if val_int == 0:
            desc = "0 px (2D Plano Duplicado)"
        elif val_int <= 10:
            desc = f"{val_int} px (Profundidad Sutil)"
        elif val_int <= 20:
            desc = f"{val_int} px (Profundidad Media)"
        else:
            desc = f"{val_int} px (Profundidad Intensa)"
        self.lbl_parallax_indicator.configure(text=desc)
        self._on_params_changed()

    def _on_params_changed(self) -> None:
        """
        Invocado cuando cambia cualquier parámetro visual para actualizar la previsualización en vivo.
        """
        self._render_live_preview_from_cache()

    # --------------------------------------------------------------------------
    # SISTEMA DE VISTA PREVIA EN VIVO (LIVE PREVIEW)
    # --------------------------------------------------------------------------
    def _load_source_frame_and_update_preview(self) -> None:
        """
        Extrae en un hilo secundario el fotograma original y renderiza la vista previa.
        """
        if not self.selected_preview_item:
            return

        file_path = self.selected_preview_item.file_path
        self.lbl_preview_canvas.configure(image="", text=self.loc_mgr.t("preview_loading"))

        def _worker() -> None:
            frame = self.processor.extract_preview_frame(file_path, timestamp_sec=1.0)
            self._cached_source_frame = frame
            self._cached_source_path = file_path
            self.after(0, self._render_live_preview_from_cache)

        threading.Thread(target=_worker, daemon=True).start()

    def _render_live_preview_from_cache(self) -> None:
        """
        Renderiza instantáneamente (3 ms) la composición estereoscópica con esquinas redondeadas
        usando el fotograma fuente en memoria y actualiza la tarjeta de vista previa.
        """
        if self._cached_source_frame is None:
            if not self.queue_items:
                self.lbl_preview_canvas.configure(image="", text=self.loc_mgr.t("preview_no_file"))
            return

        options = self._gather_conversion_options()

        # Compone la vista previa con el motor de máscaras ópticas
        try:
            target_canvas_w = 960
            target_canvas_h = 540

            sbs_composite = LensMaskGenerator.compose_preview_sbs(
                source_frame=self._cached_source_frame,
                target_canvas_w=target_canvas_w,
                target_canvas_h=target_canvas_h,
                aspect_mode=options.aspect_mode,
                fit_mode=options.fit_mode,
                corner_radius_pct=options.corner_radius_pct,
                margin_pct=options.margin_pct,
                center_gap_pct=options.center_gap_pct,
                parallax_px=options.parallax_depth,
                content_scale=options.content_scale
            )
            self._last_composed_preview = sbs_composite

            # Calculamos tamaño de visualización dentro de la caja de vista previa
            box_w = max(100, self.preview_box.winfo_width())
            box_h = max(80, self.preview_box.winfo_height())
            ratio = min(box_w / target_canvas_w, box_h / target_canvas_h)
            disp_w = max(60, int(target_canvas_w * ratio))
            disp_h = max(40, int(target_canvas_h * ratio))

            ctk_img = ctk.CTkImage(light_image=sbs_composite, dark_image=sbs_composite, size=(disp_w, disp_h))
            self.lbl_preview_canvas.configure(image=ctk_img, text="")
            self.lbl_preview_canvas.image = ctk_img

            # Actualizamos pie descriptivo
            file_name = self.selected_preview_item.file_name if self.selected_preview_item else ""
            asp_str = options.aspect_mode.upper()
            fov_pct = int(round(options.content_scale * 100))
            rad_pct = int(options.corner_radius_pct * 100)
            self.lbl_preview_footer.configure(
                text=f"{file_name}  |  Aspecto: {asp_str}  |  FOV: {fov_pct}%  |  Esquinas: {rad_pct}%  |  Parallax: {options.parallax_depth}px"
            )

        except Exception as error:
            self.lbl_preview_canvas.configure(image="", text=f"Error en vista previa: {error}")

    def _on_refresh_preview_clicked(self) -> None:
        """
        Fuerza la recarga del fotograma desde el medio y refresca el visor.
        """
        self._load_source_frame_and_update_preview()

    def _on_enlarge_preview(self) -> None:
        """
        Abre la ventana modal ampliada para ver la imagen en alta definición.
        """
        if self._last_composed_preview is None:
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_warning_title"),
                self.loc_mgr.t("preview_no_file"),
                "warning"
            )
            return

        ModernPreviewModal(
            parent=self.winfo_toplevel(),
            preview_image=self._last_composed_preview,
            title=self.loc_mgr.t("preview_modal_title")
        )

    # --------------------------------------------------------------------------
    # RECOPILACIÓN DE PARÁMETROS Y CONTROL DE CONVERSIÓN
    # --------------------------------------------------------------------------
    def _gather_conversion_options(self) -> ConversionOptions:
        """
        Recopila los parámetros seleccionados en la interfaz y crea un objeto ConversionOptions.
        """
        # Plantilla
        template_choice = self.opt_template.get()
        chosen_id = "virtual_cinema_full"
        for k in self.template_keys:
            if self.loc_mgr.t(LensMaskGenerator.PRESET_TEMPLATES[k].name_key) == template_choice:
                chosen_id = k
                break

        # Relación de aspecto
        aspect_choice = self.opt_aspect.get()
        if "1:1" in aspect_choice:
            aspect_opt = "1:1"
        elif "4:3" in aspect_choice:
            aspect_opt = "4:3"
        elif "16:9" in aspect_choice:
            aspect_opt = "16:9"
        elif "Original" in aspect_choice:
            aspect_opt = "original"
        else:
            aspect_opt = "fill"

        # Modo de ajuste
        fit_choice = self.opt_fit.get()
        fit_opt = "crop" if ("Rellenar" in fit_choice or "Crop" in fit_choice or "Inmersivo" in fit_choice) else "fit"

        # Curvatura y márgenes
        corner_r = float(self.slider_corner_radius.get())
        margin_val = float(self.slider_margin.get())
        gap_val = float(self.slider_center_gap.get())

        # Escala FOV
        scale_val = float(self.slider_content_scale.get())

        # Resolución
        res_text = self.opt_res.get()
        if "720p" in res_text:
            res_opt = "720p"
        elif "1080p" in res_text:
            res_opt = "1080p"
        elif "1440p" in res_text:
            res_opt = "1440p"
        elif "4k" in res_text or "2160p" in res_text:
            res_opt = "4k"
        else:
            res_opt = "original"

        # Contenedor
        container_opt = "mkv" if "mkv" in self.opt_container.get().lower() else "mp4"

        # Codificador
        enc_text = self.opt_encoder.get()
        if "NVENC" in enc_text:
            encoder_opt = "nvenc"
        elif "QSV" in enc_text:
            encoder_opt = "qsv"
        elif "AMF" in enc_text:
            encoder_opt = "amf"
        else:
            encoder_opt = "cpu"

        # Calidad CRF y Parallax
        crf_val = int(round(self.slider_crf.get()))
        parallax_val = int(round(self.slider_parallax.get()))

        # Audio
        audio_text = self.opt_audio.get()
        audio_opt = "aac" if "AAC" in audio_text else "copy"

        # Directorio de exportación
        export_dir = self.config_mgr.ensure_export_directory()

        return ConversionOptions(
            mode="custom" if chosen_id == "custom" else "auto",
            template_id=chosen_id,
            aspect_mode=aspect_opt,
            fit_mode=fit_opt,
            corner_radius_pct=corner_r,
            margin_pct=margin_val,
            center_gap_pct=gap_val,
            content_scale=scale_val,
            sbs_mode="half",
            resolution=res_opt,
            container=container_opt,
            crf=crf_val,
            encoder=encoder_opt,
            parallax_depth=parallax_val,
            audio_codec=audio_opt,
            export_directory=export_dir
        )

    def _on_start_conversion(self) -> None:
        """
        Inicia la conversión de la cola en un hilo de trabajo secundario (threading).
        """
        if self.is_converting:
            return

        if not self.queue_items:
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_warning_title"),
                self.loc_mgr.t("no_files_selected_msg"),
                "warning"
            )
            return

        if not self.processor.is_ffmpeg_installed():
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("ffmpeg_missing_title"),
                self.loc_mgr.t("ffmpeg_missing_msg"),
                "error"
            )
            return

        options = self._gather_conversion_options()
        self.is_converting = True

        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.btn_import.configure(state="disabled")
        self.btn_clear.configure(state="disabled")

        worker = threading.Thread(target=self._conversion_worker, args=(options,), daemon=True)
        worker.start()

    def _conversion_worker(self, options: ConversionOptions) -> None:
        """
        Función ejecutada dentro del hilo secundario que procesa cada archivo de la cola.
        """
        self.append_log("=== Iniciando sesión de transcodificación multimedia ===")
        total_items = len(self.queue_items)
        completed_count = 0

        for index, item in enumerate(self.queue_items):
            if not self.is_converting:
                break

            self._update_item_status(item, "processing")
            self._update_overall_progress(index, total_items)

            def on_progress(frac: float, status_text: str) -> None:
                self.after(0, lambda: self._apply_file_progress(frac, status_text))

            success = self.processor.convert_item(
                item=item,
                options=options,
                progress_callback=on_progress,
                log_callback=self.append_log
            )

            if success:
                self._update_item_status(item, "completed")
                completed_count += 1
            else:
                if item.status == "cancelled":
                    self._update_item_status(item, "cancelled")
                    break
                else:
                    self._update_item_status(item, "error")

        self.is_converting = False
        self._update_overall_progress(completed_count, total_items)

        def _finalize_ui() -> None:
            self.btn_start.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            self.btn_import.configure(state="normal")
            self.btn_clear.configure(state="normal")

            if completed_count == total_items:
                self.append_log("=== Todos los archivos fueron convertidos con éxito ===")
                ModernMessageDialog(
                    self.winfo_toplevel(),
                    self.loc_mgr.t("conversion_finished_title"),
                    self.loc_mgr.t("conversion_finished_msg"),
                    "success"
                )
            else:
                self.append_log(f"=== Sesión finalizada: {completed_count}/{total_items} archivos procesados ===")

        self.after(0, _finalize_ui)

    def _apply_file_progress(self, frac: float, status_text: str) -> None:
        """
        Actualiza la barra de progreso del archivo actual.
        """
        self.progress_bar_file.set(frac)
        self.lbl_progress_details.configure(text=status_text)

    def _update_overall_progress(self, current_index: int, total_items: int) -> None:
        """
        Actualiza la barra de progreso global.
        """
        fraction = (current_index / total_items) if total_items > 0 else 0.0
        details = f"{current_index} / {total_items} procesados ({int(fraction * 100)}%)"

        def _update() -> None:
            self.progress_bar_overall.set(fraction)
            self.lbl_overall_details.configure(text=details)

        self.after(0, _update)

    def _update_overall_progress_labels(self) -> None:
        """
        Refresca los contadores de la cola.
        """
        total = len(self.queue_items)
        done = sum(1 for it in self.queue_items if it.status == "completed")
        fraction = (done / total) if total > 0 else 0.0
        self.progress_bar_overall.set(fraction)
        self.lbl_overall_details.configure(text=f"{done} / {total} completados")

    def _update_item_status(self, item: MediaItem, new_status: str) -> None:
        """
        Actualiza el estado visual de la insignia de un elemento en la cola.
        """
        item.status = new_status
        status_colors = {
            "pending": ("#64748b", self.loc_mgr.t("status_pending")),
            "processing": ("#0284c7", self.loc_mgr.t("status_processing")),
            "completed": ("#16a34a", self.loc_mgr.t("status_completed")),
            "error": ("#dc2626", self.loc_mgr.t("status_error")),
            "cancelled": ("#d97706", self.loc_mgr.t("status_cancelled"))
        }
        bg_c, text_status = status_colors.get(new_status, ("#64748b", new_status))

        def _update() -> None:
            widgets = self.item_widgets.get(item.file_path)
            if widgets and "status_lbl" in widgets:
                widgets["status_lbl"].configure(text=f" {text_status} ", fg_color=bg_c)

        self.after(0, _update)

    def _on_cancel_conversion(self) -> None:
        """
        Cancela el proceso activo de FFmpeg.
        """
        if not self.is_converting:
            return

        self.append_log("Solicitando cancelación de la conversión...")
        self.processor.cancel()
        self.is_converting = False

    def _update_ui_texts(self, lang_code: str) -> None:
        """
        Actualiza dinámicamente los textos de la interfaz al cambiar de idioma.
        """
        self.btn_import.configure(text=f"📂  {self.loc_mgr.t('import_files')}")
        self.btn_clear.configure(text=self.loc_mgr.t("clear_queue"))
        self.lbl_queue_title.configure(text=self.loc_mgr.t("queue_title"))
        self.lbl_empty_queue.configure(text=self.loc_mgr.t("no_files_queued"))

        self.lbl_tmpl_title.configure(text=f"🎯 {self.loc_mgr.t('label_template')}")
        self.template_names = [self.loc_mgr.t(LensMaskGenerator.PRESET_TEMPLATES[k].name_key) for k in self.template_keys]
        cur_tmpl_choice = self.opt_template.get()
        self.opt_template.configure(values=self.template_names)

        self.lbl_corner_radius.configure(text=self.loc_mgr.t("label_corner_radius"))
        self.lbl_margin.configure(text=self.loc_mgr.t("label_margin"))
        self.lbl_center_gap.configure(text=self.loc_mgr.t("label_center_gap"))
        self.lbl_aspect.configure(text=self.loc_mgr.t("label_aspect"))
        self.lbl_fit.configure(text=self.loc_mgr.t("label_fit_mode"))

        self.opt_aspect.configure(values=[
            self.loc_mgr.t("opt_aspect_1_1"),
            self.loc_mgr.t("opt_aspect_4_3"),
            self.loc_mgr.t("opt_aspect_16_9"),
            self.loc_mgr.t("opt_aspect_original"),
            self.loc_mgr.t("opt_aspect_fill")
        ])

        self.opt_fit.configure(values=[self.loc_mgr.t("opt_fit_crop"), self.loc_mgr.t("opt_fit_letterbox")])

        self.lbl_adv_title.configure(text=f"⚙️ {self.loc_mgr.t('advanced_options_title')}")
        self.lbl_res.configure(text=self.loc_mgr.t("label_resolution"))
        self.lbl_container.configure(text=self.loc_mgr.t("label_container"))
        self.lbl_enc.configure(text=self.loc_mgr.t("label_encoder"))
        self.lbl_crf_title.configure(text=self.loc_mgr.t("label_quality"))
        self.lbl_parallax.configure(text=self.loc_mgr.t("label_parallax"))
        self.lbl_audio.configure(text=self.loc_mgr.t("label_audio"))

        self.lbl_preview_title.configure(text=f"👓 {self.loc_mgr.t('preview_title')}")
        self.btn_refresh_prev.configure(text=self.loc_mgr.t("btn_refresh_preview"))
        self.btn_enlarge.configure(text=self.loc_mgr.t("btn_enlarge_preview"))

        self.btn_start.configure(text=f"▶  {self.loc_mgr.t('btn_start_conversion')}")
        self.btn_cancel.configure(text=f"⏹ {self.loc_mgr.t('btn_cancel_conversion')}")
        self.lbl_progress_file.configure(text=self.loc_mgr.t("progress_title"))
        self.lbl_progress_overall.configure(text=self.loc_mgr.t("progress_overall"))
        self.lbl_console_title.configure(text=self.loc_mgr.t("console_title"))

        self._render_queue_items()
