# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/tab_streaming.py
# DESCRIPCIÓN: Pestaña de Streaming y Proyección en Tiempo Real.
#              Permite capturar pantallas completas o ventanas específicas de
#              aplicaciones (navegadores, reproductores de video, etc.), aplicar
#              la calibración óptica SBS con esquinas redondeadas y proyectar
#              en pantalla completa sin bordes o transmitir por Wi-Fi al celular.
# ==============================================================================

import time
import threading
from typing import Optional, List, Tuple, Dict, Any
import customtkinter as ctk
from PIL import Image

from config.config_manager import ConfigManager
from core.localization import LocalizationManager
from core.lens_mask import LensMaskGenerator
from core.screen_capture import ScreenCaptureEngine
from core.stream_server import LocalStreamServer
from ui.streaming_window import StreamingWindow
from ui.dialogs import ModernMessageDialog


class StreamingTab(ctk.CTkFrame):
    """
    Pestaña principal para el control y configuración del modo Streaming en Vivo.
    Proporciona selección de fuente, calibración de lentes, proyección de escritorio
    en pantalla completa y servidor web local para celulares.
    """

    def __init__(
        self,
        parent: Any,
        config_mgr: ConfigManager,
        loc_mgr: LocalizationManager
    ) -> None:
        """
        Inicializa la pestaña de streaming en tiempo real.

        Args:
            parent (Any): Contenedor padre.
            config_mgr (ConfigManager): Gestor de configuración persistente.
            loc_mgr (LocalizationManager): Gestor de idiomas y textos.
        """
        super().__init__(parent, fg_color="transparent")

        self.config_mgr = config_mgr
        self.loc_mgr = loc_mgr

        # Motores internos de captura y servidor web local
        self.capture_engine = ScreenCaptureEngine()
        self.stream_server = LocalStreamServer()

        # Referencia a la ventana de proyección activa (si está abierta)
        self.active_projection_window: Optional[StreamingWindow] = None

        # Hilo de transmisión web en segundo plano
        self._web_stream_thread: Optional[threading.Thread] = None
        self._is_web_streaming: bool = False

        # Datos de fuentes de captura
        self._monitors: List[Dict[str, Any]] = []
        self._windows: List[Tuple[int, str]] = []

        # Parámetros ópticos en memoria
        self.current_template_id: str = "virtual_cinema_full"
        self.current_aspect_mode: str = "original"
        self.current_fit_mode: str = "fit"
        self.current_corner_radius: float = 0.15
        self.current_margin: float = 0.04
        self.current_center_gap: float = 0.04
        self.current_parallax: int = 0
        self.current_content_scale: float = 0.95
        self.current_fps: int = 60

        # Suscripción a cambios de idioma
        self.loc_mgr.add_listener(self._update_ui_texts)

        # Construcción visual de componentes
        self._build_ui()

        # Cargar monitores y ventanas iniciales
        self._refresh_sources()

    def _build_ui(self) -> None:
        """
        Construye la arquitectura visual de la pestaña con paneles de control responsivos.
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Contenedor desplazable principal
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        # ----------------------------------------------------------------------
        # TARJETA 1: Fuente de Captura en Vivo (Izquierda)
        # ----------------------------------------------------------------------
        self.card_source = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.card_source.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.card_source.grid_columnconfigure(0, weight=1)

        self.lbl_source_title = ctk.CTkLabel(
            self.card_source,
            text=f"📺 {self.loc_mgr.t('stream_source_title')}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_source_title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # Selector de tipo de captura (Monitor vs Ventana)
        self.source_type_var = ctk.StringVar(value="monitor")
        self.seg_source_type = ctk.CTkSegmentedButton(
            self.card_source,
            values=["🖥️ Pantalla", "🪟 Ventana de App"],
            command=self._on_source_type_toggled
        )
        self.seg_source_type.set("🖥️ Pantalla")
        self.seg_source_type.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Contenedor para Monitores
        self.frame_monitor_select = ctk.CTkFrame(self.card_source, fg_color="transparent")
        self.frame_monitor_select.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        self.frame_monitor_select.grid_columnconfigure(1, weight=1)

        self.lbl_monitor = ctk.CTkLabel(self.frame_monitor_select, text="Monitor:", font=ctk.CTkFont(size=12))
        self.lbl_monitor.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.opt_monitors = ctk.CTkOptionMenu(
            self.frame_monitor_select,
            values=["Cargando monitores..."],
            command=self._on_monitor_selected
        )
        self.opt_monitors.grid(row=0, column=1, sticky="ew")

        # Contenedor para Ventanas de Aplicaciones
        self.frame_window_select = ctk.CTkFrame(self.card_source, fg_color="transparent")
        self.frame_window_select.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        self.frame_window_select.grid_columnconfigure(0, weight=1)

        self.opt_windows = ctk.CTkOptionMenu(
            self.frame_window_select,
            values=["Cargando ventanas..."]
        )
        self.opt_windows.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.btn_refresh_windows = ctk.CTkButton(
            self.frame_window_select,
            text=self.loc_mgr.t("stream_btn_refresh_windows"),
            fg_color="#334155",
            hover_color="#475569",
            height=28,
            command=self._refresh_sources
        )
        self.btn_refresh_windows.grid(row=1, column=0, sticky="ew")
        self.frame_window_select.grid_remove()  # Oculto por omisión

        # Selector de Tasa de Refresco (FPS)
        frame_fps = ctk.CTkFrame(self.card_source, fg_color="transparent")
        frame_fps.grid(row=4, column=0, sticky="ew", padx=15, pady=(15, 15))
        frame_fps.grid_columnconfigure(1, weight=1)

        self.lbl_fps = ctk.CTkLabel(
            frame_fps,
            text=self.loc_mgr.t("stream_fps_label"),
            font=ctk.CTkFont(size=12)
        )
        self.lbl_fps.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.seg_fps = ctk.CTkSegmentedButton(
            frame_fps,
            values=["30 FPS", "60 FPS"],
            command=self._on_fps_changed
        )
        self.seg_fps.set("60 FPS")
        self.seg_fps.grid(row=0, column=1, sticky="ew")

        # ----------------------------------------------------------------------
        # TARJETA 2: Calibración Óptica y Formato SBS (Derecha)
        # ----------------------------------------------------------------------
        self.card_optical = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.card_optical.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.card_optical.grid_columnconfigure(1, weight=1)

        self.lbl_optical_title = ctk.CTkLabel(
            self.card_optical,
            text=f"🥽 {self.loc_mgr.t('stream_optical_title')}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_optical_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))

        # Selector de Plantillas Ópticas
        lbl_template = ctk.CTkLabel(self.card_optical, text="Plantilla:", font=ctk.CTkFont(size=12))
        lbl_template.grid(row=1, column=0, sticky="w", padx=15, pady=4)

        template_display_names = [
            "Cine Virtual Completo (100% Contenido / Sin Recorte)",
            "VR Shinecon 1:1 (Lentes Cuadradas / Anti-estiramiento)",
            "VR180 Domo Estereoscópico",
            "Cine Virtual 16:9 Flotante",
            "Formato Óptico 4:3 Clásico",
            "Half SBS Estándar (Pantalla Completa)",
            "Personalizado"
        ]
        self.opt_templates = ctk.CTkOptionMenu(
            self.card_optical,
            values=template_display_names,
            command=self._on_template_selected
        )
        self.opt_templates.set(template_display_names[0])
        self.opt_templates.grid(row=1, column=1, sticky="ew", padx=15, pady=4)

        # Control deslizante: Esquinas redondeadas
        self.lbl_corner = ctk.CTkLabel(self.card_optical, text="Curvatura:", font=ctk.CTkFont(size=12))
        self.lbl_corner.grid(row=2, column=0, sticky="w", padx=15, pady=4)

        self.slider_corner = ctk.CTkSlider(
            self.card_optical,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            command=self._on_slider_changed
        )
        self.slider_corner.set(0.15)
        self.slider_corner.grid(row=2, column=1, sticky="ew", padx=15, pady=4)

        # Control deslizante: Margen exterior
        self.lbl_margin = ctk.CTkLabel(self.card_optical, text="Borde Negro:", font=ctk.CTkFont(size=12))
        self.lbl_margin.grid(row=3, column=0, sticky="w", padx=15, pady=4)

        self.slider_margin = ctk.CTkSlider(
            self.card_optical,
            from_=0.0,
            to=0.20,
            number_of_steps=100,
            command=self._on_slider_changed
        )
        self.slider_margin.set(0.04)
        self.slider_margin.grid(row=3, column=1, sticky="ew", padx=15, pady=4)

        # Control deslizante: Separación central
        self.lbl_gap = ctk.CTkLabel(self.card_optical, text="Separador:", font=ctk.CTkFont(size=12))
        self.lbl_gap.grid(row=4, column=0, sticky="w", padx=15, pady=4)

        self.slider_gap = ctk.CTkSlider(
            self.card_optical,
            from_=0.0,
            to=0.20,
            number_of_steps=100,
            command=self._on_slider_changed
        )
        self.slider_gap.set(0.04)
        self.slider_gap.grid(row=4, column=1, sticky="ew", padx=15, pady=4)

        # Control deslizante: Profundidad Parallax 3D
        self.lbl_parallax = ctk.CTkLabel(self.card_optical, text="Profundidad 3D:", font=ctk.CTkFont(size=12))
        self.lbl_parallax.grid(row=5, column=0, sticky="w", padx=15, pady=4)

        self.slider_parallax = ctk.CTkSlider(
            self.card_optical,
            from_=-30,
            to=30,
            number_of_steps=60,
            command=self._on_slider_changed
        )
        self.slider_parallax.set(0)
        self.slider_parallax.grid(row=5, column=1, sticky="ew", padx=15, pady=4)

        # Control: Modo de Ajuste en Ventana (Fit vs Crop)
        self.lbl_fit = ctk.CTkLabel(self.card_optical, text="Modo de Ajuste:", font=ctk.CTkFont(size=12))
        self.lbl_fit.grid(row=6, column=0, sticky="w", padx=15, pady=4)

        self.opt_fit = ctk.CTkOptionMenu(
            self.card_optical,
            values=[
                "Ajustar al Marco (100% Visible / Sin recortes)",
                "Rellenar Lente (Recorte inmersivo)"
            ],
            command=self._on_fit_mode_selected
        )
        self.opt_fit.set("Ajustar al Marco (100% Visible / Sin recortes)")
        self.opt_fit.grid(row=6, column=1, sticky="ew", padx=15, pady=4)

        # Control deslizante: Escala / FOV (Zoom de Pantalla)
        self.lbl_scale = ctk.CTkLabel(self.card_optical, text="Escala / FOV:", font=ctk.CTkFont(size=12))
        self.lbl_scale.grid(row=7, column=0, sticky="w", padx=15, pady=4)

        self.slider_scale = ctk.CTkSlider(
            self.card_optical,
            from_=0.50,
            to=1.50,
            number_of_steps=100,
            command=self._on_slider_changed
        )
        self.slider_scale.set(0.95)
        self.slider_scale.grid(row=7, column=1, sticky="ew", padx=15, pady=4)

        self.lbl_scale_indicator = ctk.CTkLabel(
            self.card_optical,
            text="95% (Pantalla Alejada / 100% Contenido Visible)",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_scale_indicator.grid(row=8, column=1, sticky="w", padx=15, pady=(0, 4))

        # Indicador de atajo de teclado y rueda del ratón
        self.lbl_zoom_hint = ctk.CTkLabel(
            self.card_optical,
            text="💡 En Pantalla Completa: Rueda del Ratón o teclas + / - para Zoom en vivo",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#38bdf8"
        )
        self.lbl_zoom_hint.grid(row=9, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 15))

        # ----------------------------------------------------------------------
        # TARJETA 3: Proyección en Pantalla Completa en la PC (Fila 1, span 2)
        # ----------------------------------------------------------------------
        self.card_projector = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color=("#f1f5f9", "#111827"))
        self.card_projector.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.card_projector.grid_columnconfigure(0, weight=1)

        self.btn_launch_projection = ctk.CTkButton(
            self.card_projector,
            text=self.loc_mgr.t("stream_btn_start_projection"),
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._launch_projection_window
        )
        self.btn_launch_projection.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 6))

        lbl_proj_hint = ctk.CTkLabel(
            self.card_projector,
            text="💡 Abre una ventana sin bordes para mover a tu monitor secundario o pantalla proyectada. Pulsa F11 o Doble Clic para Pantalla Completa.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_proj_hint.grid(row=1, column=0, padx=20, pady=(0, 15))

        # ----------------------------------------------------------------------
        # TARJETA 4: Servidor Web Local para el Celular (Fila 2, span 2)
        # ----------------------------------------------------------------------
        self.card_web = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.card_web.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.card_web.grid_columnconfigure(0, weight=1)

        # Encabezado con switch
        header_web = ctk.CTkFrame(self.card_web, fg_color="transparent")
        header_web.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 8))
        header_web.grid_columnconfigure(0, weight=1)

        self.lbl_web_title = ctk.CTkLabel(
            header_web,
            text=f"📡 {self.loc_mgr.t('stream_web_title')}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_web_title.grid(row=0, column=0, sticky="w")

        self.switch_web_server = ctk.CTkSwitch(
            header_web,
            text=self.loc_mgr.t("stream_web_switch"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_toggle_web_server
        )
        self.switch_web_server.grid(row=0, column=1, sticky="e")

        # Contenedor de estado y URL
        self.frame_url_box = ctk.CTkFrame(self.card_web, fg_color=("#e2e8f0", "#1e293b"), corner_radius=8)
        self.frame_url_box.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.frame_url_box.grid_columnconfigure(1, weight=1)

        self.lbl_status_badge = ctk.CTkLabel(
            self.frame_url_box,
            text="⚪ Servidor Web Detenido",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_status_badge.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 4))

        self.lbl_url_prompt = ctk.CTkLabel(
            self.frame_url_box,
            text=self.loc_mgr.t("stream_web_url_label"),
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.lbl_url_prompt.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 8))

        self.entry_stream_url = ctk.CTkEntry(
            self.frame_url_box,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="readonly",
            height=34
        )
        self.entry_stream_url.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(15, 10), pady=(0, 12))
        self._set_url_text(self.stream_server.get_url())

        self.btn_copy_url = ctk.CTkButton(
            self.frame_url_box,
            text=self.loc_mgr.t("stream_web_copy"),
            width=120,
            height=34,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._copy_url_to_clipboard
        )
        self.btn_copy_url.grid(row=2, column=2, sticky="e", padx=(0, 15), pady=(0, 12))

        self.lbl_web_help = ctk.CTkLabel(
            self.frame_url_box,
            text=self.loc_mgr.t("stream_help_note"),
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8"
        )
        self.lbl_web_help.grid(row=3, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 12))

    # --------------------------------------------------------------------------
    # Gestión de Fuentes de Captura
    # --------------------------------------------------------------------------

    def _refresh_sources(self) -> None:
        """
        Escanea y actualiza la lista de pantallas y ventanas disponibles en Windows.
        """
        # Actualizamos monitores
        self._monitors = self.capture_engine.get_monitors()
        monitor_names = [m["name"] for m in self._monitors]
        if monitor_names:
            self.opt_monitors.configure(values=monitor_names)
            # Seleccionamos monitor principal (índice 1 si existe, o 0)
            def_idx = 1 if len(monitor_names) > 1 else 0
            self.opt_monitors.set(monitor_names[def_idx])

        # Actualizamos ventanas de aplicaciones
        self._windows = self.capture_engine.get_open_windows()
        window_titles = [f"🪟 {title[:45]}..." if len(title) > 45 else f"🪟 {title}" for _, title in self._windows]
        if window_titles:
            self.opt_windows.configure(values=window_titles)
            self.opt_windows.set(window_titles[0])
        else:
            self.opt_windows.configure(values=["No se detectaron ventanas abiertas"])
            self.opt_windows.set("No se detectaron ventanas abiertas")

    def _on_source_type_toggled(self, value: str) -> None:
        """
        Alterna la visibilidad entre el selector de monitor y el selector de ventana.
        """
        if "Pantalla" in value:
            self.source_type_var.set("monitor")
            self.frame_window_select.grid_remove()
            self.frame_monitor_select.grid()
        else:
            self.source_type_var.set("window")
            self.frame_monitor_select.grid_remove()
            self.frame_window_select.grid()

    def _on_monitor_selected(self, choice: str) -> None:
        """
        Maneja la selección de un monitor específico.
        """
        pass

    def _get_current_source_info(self) -> Tuple[str, int]:
        """
        Obtiene el tipo y el ID numérico de la fuente de captura seleccionada.

        Returns:
            Tuple[str, int]: ('monitor'|'window', id_monitor_o_hwnd)
        """
        stype = self.source_type_var.get()
        if stype == "monitor":
            selected_name = self.opt_monitors.get()
            for m in self._monitors:
                if m["name"] == selected_name:
                    return "monitor", m["index"]
            return "monitor", 1
        else:
            selected_str = self.opt_windows.get()
            for idx, (_, title) in enumerate(self._windows):
                if title in selected_str or selected_str.replace("🪟 ", "").rstrip("...") in title:
                    return "window", self._windows[idx][0]
            return "monitor", 1

    # --------------------------------------------------------------------------
    # Parámetros Ópticos y Plantillas
    # --------------------------------------------------------------------------

    def _on_template_selected(self, choice: str) -> None:
        """
        Aplica los parámetros de la plantilla óptica seleccionada.
        """
        if "Completo" in choice or "Sin Recorte" in choice:
            self.current_template_id = "virtual_cinema_full"
            self.current_aspect_mode = "original"
            self.current_fit_mode = "fit"
            self.current_corner_radius = 0.15
            self.current_margin = 0.04
            self.current_center_gap = 0.04
            self.current_content_scale = 0.95
        elif "1:1" in choice:
            self.current_template_id = "vr_shinecon_1_1"
            self.current_aspect_mode = "1:1"
            self.current_fit_mode = "crop"
            self.current_corner_radius = 0.45
            self.current_margin = 0.04
            self.current_center_gap = 0.04
            self.current_content_scale = 1.0
        elif "VR180" in choice:
            self.current_template_id = "vr180_lens_mask"
            self.current_aspect_mode = "1:1"
            self.current_fit_mode = "crop"
            self.current_corner_radius = 0.75
            self.current_margin = 0.03
            self.current_center_gap = 0.05
            self.current_content_scale = 1.0
        elif "16:9" in choice:
            self.current_template_id = "virtual_cinema_16_9"
            self.current_aspect_mode = "16:9"
            self.current_fit_mode = "fit"
            self.current_corner_radius = 0.25
            self.current_margin = 0.08
            self.current_center_gap = 0.06
            self.current_content_scale = 1.0
        elif "4:3" in choice:
            self.current_template_id = "classic_optical_4_3"
            self.current_aspect_mode = "4:3"
            self.current_fit_mode = "crop"
            self.current_corner_radius = 0.35
            self.current_margin = 0.04
            self.current_center_gap = 0.04
            self.current_content_scale = 1.0
        elif "Half SBS" in choice:
            self.current_template_id = "half_sbs_fullscreen"
            self.current_aspect_mode = "fill"
            self.current_fit_mode = "crop"
            self.current_corner_radius = 0.0
            self.current_margin = 0.0
            self.current_center_gap = 0.0
            self.current_content_scale = 1.0
        else:
            self.current_template_id = "custom"

        # Actualizamos los controles deslizantes
        self.slider_corner.set(self.current_corner_radius)
        self.slider_margin.set(self.current_margin)
        self.slider_gap.set(self.current_center_gap)
        self.slider_scale.set(self.current_content_scale)
        self.opt_fit.set("Ajustar al Marco (100% Visible / Sin recortes)" if self.current_fit_mode == "fit" else "Rellenar Lente (Recorte inmersivo)")
        pct = int(round(self.current_content_scale * 100))
        self.lbl_scale_indicator.configure(text=f"{pct}% (Campo de Visión)")

        # Notificamos a la ventana de proyección si está abierta
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.apply_template(self.current_template_id)

    def _on_fit_mode_selected(self, choice: str) -> None:
        """
        Ajusta el modo de encaje de la imagen entre ajuste completo o recorte inmersivo.
        """
        self.current_fit_mode = "crop" if "Rellenar" in choice else "fit"
        self.current_template_id = "custom"
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.fit_mode = self.current_fit_mode

    def _on_slider_changed(self, _val: Any = None) -> None:
        """
        Sincroniza valores personalizados de los deslizadores ópticos.
        """
        self.current_corner_radius = self.slider_corner.get()
        self.current_margin = self.slider_margin.get()
        self.current_center_gap = self.slider_gap.get()
        self.current_parallax = int(self.slider_parallax.get())
        self.current_content_scale = round(self.slider_scale.get(), 2)
        pct = int(round(self.current_content_scale * 100))
        if pct == 100:
            desc = "100% (Tamaño de Ventana Estándar)"
        elif pct < 100:
            desc = f"{pct}% (Pantalla Alejada / 100% Contenido Visible)"
        else:
            desc = f"{pct}% (Zoom / Acercamiento Inmersivo)"
        self.lbl_scale_indicator.configure(text=desc)
        self.current_template_id = "custom"

        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.corner_radius_pct = self.current_corner_radius
            self.active_projection_window.margin_pct = self.current_margin
            self.active_projection_window.center_gap_pct = self.current_center_gap
            self.active_projection_window.parallax_px = self.current_parallax
            self.active_projection_window.fit_mode = self.current_fit_mode
            self.active_projection_window.set_zoom(self.current_content_scale)

    def _on_fps_changed(self, choice: str) -> None:
        """
        Ajusta la tasa de fotogramas por segundo deseada.
        """
        self.current_fps = 60 if "60" in choice else 30
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.target_fps = self.current_fps

    # --------------------------------------------------------------------------
    # Lanzamiento de Proyección en Pantalla Completa
    # --------------------------------------------------------------------------

    def _launch_projection_window(self) -> None:
        """
        Abre o enfoca la ventana dedicada de proyección SBS en tiempo real.
        """
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.focus()
            self.active_projection_window.lift()
            return

        source_type, source_id = self._get_current_source_info()

        # Instanciamos la ventana de proyección
        self.active_projection_window = StreamingWindow(
            parent=self.winfo_toplevel(),
            capture_engine=self.capture_engine,
            stream_server=self.stream_server if self._is_web_streaming else None,
            source_type=source_type,
            source_id=source_id,
            template_id=self.current_template_id,
            aspect_mode=self.current_aspect_mode,
            fit_mode=self.current_fit_mode,
            corner_radius_pct=self.current_corner_radius,
            margin_pct=self.current_margin,
            center_gap_pct=self.current_center_gap,
            parallax_px=self.current_parallax,
            target_fps=self.current_fps,
            content_scale=self.current_content_scale,
            on_close_callback=self._on_projection_closed
        )

    def _on_projection_closed(self) -> None:
        """
        Callback ejecutada al cerrarse la ventana de proyección en tiempo real.
        """
        self.active_projection_window = None

    # --------------------------------------------------------------------------
    # Servidor Web Móvil Local (Wi-Fi)
    # --------------------------------------------------------------------------

    def _on_toggle_web_server(self) -> None:
        """
        Enciende o apaga el servidor local de streaming MJPEG/HTTP.
        """
        if self.switch_web_server.get():
            self._start_web_server()
        else:
            self._stop_web_server()

    def _start_web_server(self) -> None:
        """
        Inicia el servidor HTTP y el bucle de difusión en segundo plano.
        """
        success = self.stream_server.start(port=5000)
        if not success:
            ModernMessageDialog(
                self.winfo_toplevel(),
                "Error de Servidor",
                "No se pudo iniciar el servidor web en el puerto 5000. Verifica que el puerto no esté en uso.",
                "error"
            )
            self.switch_web_server.deselect()
            return

        self._is_web_streaming = True
        self._set_url_text(self.stream_server.get_url())
        self.lbl_status_badge.configure(
            text="🟢 " + self.loc_mgr.t("stream_web_status_on"),
            text_color="#22c55e"
        )

        # Si la ventana de proyección ya está abierta, le compartimos el servidor
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.stream_server = self.stream_server

        # Iniciamos hilo independiente de captura y codificación para el streaming web
        self._web_stream_thread = threading.Thread(
            target=self._web_streaming_loop,
            daemon=True,
            name="VRWebStreamThread"
        )
        self._web_stream_thread.start()

    def _stop_web_server(self) -> None:
        """
        Detiene el servidor HTTP y libera el socket de red.
        """
        self._is_web_streaming = False
        self.stream_server.stop()
        self.lbl_status_badge.configure(
            text="⚪ " + self.loc_mgr.t("stream_web_status_off"),
            text_color="#94a3b8"
        )

        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.stream_server = None

    def _web_streaming_loop(self) -> None:
        """
        Bucle de captura y distribución para el servidor web móvil.
        Funciona autónomamente incluso si la ventana de proyección no está abierta.
        """
        target_delay = 1.0 / max(15, min(60, self.current_fps))

        while self._is_web_streaming and self.stream_server.is_running():
            # Si la ventana de proyección ya está alimentando el servidor, cedemos el turno
            if (self.active_projection_window and 
                self.active_projection_window.winfo_exists() and 
                not self.active_projection_window.is_paused):
                time.sleep(0.1)
                continue

            loop_start = time.time()
            try:
                source_type, source_id = self._get_current_source_info()
                frame = self.capture_engine.capture(source_type, source_id)
                if frame is not None:
                    # Componemos SBS óptico optimizado para móvil (resolución estándar 1920x1080)
                    sbs_frame = LensMaskGenerator.compose_preview_sbs(
                        source_frame=frame,
                        target_canvas_w=1920,
                        target_canvas_h=1080,
                        aspect_mode=self.current_aspect_mode,
                        fit_mode=self.current_fit_mode,
                        corner_radius_pct=self.current_corner_radius,
                        margin_pct=self.current_margin,
                        center_gap_pct=self.current_center_gap,
                        parallax_px=self.current_parallax,
                        content_scale=self.current_content_scale
                    )
                    self.stream_server.update_frame(sbs_frame, quality=75)
            except Exception:
                pass

            elapsed = time.time() - loop_start
            wait_time = max(0.001, target_delay - elapsed)
            time.sleep(wait_time)

    def _set_url_text(self, text: str) -> None:
        """
        Actualiza el contenido del campo de texto de la URL de forma segura.
        """
        self.entry_stream_url.configure(state="normal")
        self.entry_stream_url.delete(0, "end")
        self.entry_stream_url.insert(0, text)
        self.entry_stream_url.configure(state="readonly")

    def _copy_url_to_clipboard(self) -> None:
        """
        Copia la URL local al portapapeles del sistema operativo.
        """
        url = self.entry_stream_url.get()
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.btn_copy_url.configure(text="¡Copiado! ✓")
            self.after(2000, lambda: self.btn_copy_url.configure(text=self.loc_mgr.t("stream_web_copy")))

    # --------------------------------------------------------------------------
    # Idioma y Cierre Limpio
    # --------------------------------------------------------------------------

    def _update_ui_texts(self, _lang: str) -> None:
        """
        Actualiza los textos dinámicos al cambiar el idioma de la aplicación.
        """
        try:
            self.lbl_source_title.configure(text=f"📺 {self.loc_mgr.t('stream_source_title')}")
            self.btn_refresh_windows.configure(text=self.loc_mgr.t("stream_btn_refresh_windows"))
            self.lbl_fps.configure(text=self.loc_mgr.t("stream_fps_label"))
            self.lbl_optical_title.configure(text=f"🥽 {self.loc_mgr.t('stream_optical_title')}")
            self.btn_launch_projection.configure(text=self.loc_mgr.t("stream_btn_start_projection"))
            self.lbl_web_title.configure(text=f"📡 {self.loc_mgr.t('stream_web_title')}")
            self.switch_web_server.configure(text=self.loc_mgr.t("stream_web_switch"))
            self.lbl_url_prompt.configure(text=self.loc_mgr.t("stream_web_url_label"))
            self.btn_copy_url.configure(text=self.loc_mgr.t("stream_web_copy"))
            self.lbl_web_help.configure(text=self.loc_mgr.t("stream_help_note"))

            if self._is_web_streaming:
                self.lbl_status_badge.configure(text="🟢 " + self.loc_mgr.t("stream_web_status_on"))
            else:
                self.lbl_status_badge.configure(text="⚪ " + self.loc_mgr.t("stream_web_status_off"))
        except Exception:
            pass

    def stop_all(self) -> None:
        """
        Detiene todos los servicios activos (servidor web, hilos de captura, proyección).
        """
        self._stop_web_server()
        if self.active_projection_window and self.active_projection_window.winfo_exists():
            self.active_projection_window.destroy()
            self.active_projection_window = None
