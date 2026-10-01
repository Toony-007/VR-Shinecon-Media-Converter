# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/streaming_window.py
# DESCRIPCIÓN: Ventana dedicada de proyección estereoscópica en tiempo real.
#              Soporta Pantalla Completa Sin Bordes (Borderless Fullscreen),
#              atajos de teclado (F11, Esc, Doble clic), controles flotantes HUD
#              auto-ocultables y renderizado continuo a 30/60 FPS.
# ==============================================================================

import sys
import time
import ctypes
from ctypes import wintypes
import threading
from typing import Optional, Callable, Any
import customtkinter as ctk
from PIL import Image

from core.lens_mask import LensMaskGenerator
from core.screen_capture import ScreenCaptureEngine
from core.stream_server import LocalStreamServer


class StreamingWindow(ctk.CTkToplevel):
    """
    Ventana de visualización y proyección en vivo en formato Side-by-Side (SBS).
    Permite arrastrarse a un segundo monitor, proyectarse en pantalla completa sin bordes
    o retransmitirse al visor VR en el celular.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        capture_engine: ScreenCaptureEngine,
        stream_server: Optional[LocalStreamServer] = None,
        source_type: str = "monitor",
        source_id: int = 1,
        template_id: str = "vr_shinecon_1_1",
        aspect_mode: str = "1:1",
        fit_mode: str = "crop",
        corner_radius_pct: float = 0.45,
        margin_pct: float = 0.04,
        center_gap_pct: float = 0.04,
        parallax_px: int = 0,
        target_fps: int = 60,
        content_scale: float = 1.0,
        on_close_callback: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Inicializa la ventana de proyección en tiempo real.
        """
        super().__init__(parent)

        self.capture_engine = capture_engine
        self.stream_server = stream_server
        self.source_type = source_type      # 'monitor' o 'window'
        self.source_id = source_id          # Índice de monitor o HWND de ventana
        self.template_id = template_id
        self.aspect_mode = aspect_mode
        self.fit_mode = fit_mode
        self.corner_radius_pct = corner_radius_pct
        self.margin_pct = margin_pct
        self.center_gap_pct = center_gap_pct
        self.parallax_px = parallax_px
        self.target_fps = target_fps
        self.content_scale = content_scale  # Escala de campo de visión FOV (0.5 a 1.5)
        self.on_close_callback = on_close_callback

        # Configuración de ventana base
        self.title("VR Shinecon - Proyección SBS en Tiempo Real")
        self.geometry("1100x650")
        self.minsize(640, 360)
        self.configure(fg_color="#000000")

        # Control de estado de pantalla completa
        self.is_fullscreen: bool = False
        self.is_paused: bool = False
        self._is_running: bool = True

        # Métricas de rendimiento en vivo
        self.fps_counter: int = 0
        self.current_fps: float = 0.0
        self.last_fps_time: float = time.time()

        # Configuración del sistema de rejilla (Grid)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Lienzo principal para mostrar la transmisión
        self.lbl_canvas = ctk.CTkLabel(self, text="", fg_color="#000000")
        self.lbl_canvas.grid(row=0, column=0, sticky="nsew")

        # Controles flotantes HUD (Heads-Up Display)
        self._build_floating_hud()

        # Vinculación de atajos de teclado y eventos del ratón
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._on_escape())
        self.bind("<space>", lambda e: self.toggle_pause())
        self.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.lbl_canvas.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.lbl_canvas.bind("<Button-1>", lambda e: self.focus_set())
        self.bind("<Motion>", self._on_mouse_move)
        self.lbl_canvas.bind("<Motion>", self._on_mouse_move)

        # Atajos de Zoom y Escala FOV en Pantalla Completa
        self.bind("<plus>", lambda e: self.adjust_zoom(0.05))
        self.bind("<KP_Add>", lambda e: self.adjust_zoom(0.05))
        self.bind("<equal>", lambda e: self.adjust_zoom(0.05))
        self.bind("<minus>", lambda e: self.adjust_zoom(-0.05))
        self.bind("<KP_Subtract>", lambda e: self.adjust_zoom(-0.05))
        self.bind("<underscore>", lambda e: self.adjust_zoom(-0.05))
        self.bind("<0>", lambda e: self.set_zoom(1.0))
        self.bind("<r>", lambda e: self.set_zoom(1.0))
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.lbl_canvas.bind("<MouseWheel>", self._on_mouse_wheel)

        # Enlace tardío a subwidgets de Tkinter para capturar doble clic y foco
        self.after(100, self._bind_internal_canvas_events)

        # Temporizador para auto-ocultar los controles HUD
        self._hud_hide_timer: Optional[str] = None
        self._schedule_hud_hide()

        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Foco inicial para que F11 y Espacio funcionen de inmediato
        self.after(50, lambda: self.focus_force())

        # Lanzamos el hilo de captura y renderizado en vivo
        self._render_thread = threading.Thread(target=self._capture_and_stream_loop, daemon=True)
        self._render_thread.start()

    def _bind_internal_canvas_events(self) -> None:
        """
        Asegura que los eventos de doble clic y movimiento se capturen
        en los lienzos internos de CustomTkinter.
        """
        try:
            for child in (getattr(self.lbl_canvas, "_label", None), getattr(self.lbl_canvas, "_canvas", None)):
                if child is not None:
                    child.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
                    child.bind("<Motion>", self._on_mouse_move)
                    child.bind("<Button-1>", lambda e: self.focus_set())
        except Exception:
            pass

    def _build_floating_hud(self) -> None:
        """
        Construye la barra flotante de herramientas que se desvanece automáticamente.
        """
        self.hud_frame = ctk.CTkFrame(
            self,
            fg_color=("#1e293b", "#0f172a"),
            corner_radius=12,
            height=48
        )
        # Posicionamos la barra en la parte superior central
        self.hud_frame.place(relx=0.5, rely=0.04, anchor="n")

        # Insignia de estado y FPS
        self.lbl_hud_fps = ctk.CTkLabel(
            self.hud_frame,
            text="🔴 EN VIVO  |  FPS: 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#22c55e"
        )
        self.lbl_hud_fps.pack(side="left", padx=(15, 10), pady=8)

        # Botón Pausar / Reanudar
        self.btn_pause = ctk.CTkButton(
            self.hud_frame,
            text="⏸ Pausar",
            width=75,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self.toggle_pause
        )
        self.btn_pause.pack(side="left", padx=4)

        # Selector rápido de plantilla
        self.opt_hud_template = ctk.CTkOptionMenu(
            self.hud_frame,
            values=[
                "Cine Completo (100% Contenido)",
                "VR Shinecon (1:1)",
                "VR180 Máscara",
                "Cine 16:9",
                "Formato 4:3",
                "Pantalla Completa"
            ],
            width=155,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._on_hud_template_changed
        )
        self.opt_hud_template.set("Cine Completo (100% Contenido)" if self.template_id == "virtual_cinema_full" else "VR Shinecon (1:1)")
        self.opt_hud_template.pack(side="left", padx=4)

        # Controles rápidos de Zoom / FOV
        self.btn_zoom_out = ctk.CTkButton(
            self.hud_frame,
            text="➖",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.adjust_zoom(-0.05)
        )
        self.btn_zoom_out.pack(side="left", padx=(4, 2))

        self.lbl_hud_zoom = ctk.CTkLabel(
            self.hud_frame,
            text=f"🔍 {int(round(self.content_scale * 100))}%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_hud_zoom.pack(side="left", padx=2)

        self.btn_zoom_in = ctk.CTkButton(
            self.hud_frame,
            text="➕",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.adjust_zoom(0.05)
        )
        self.btn_zoom_in.pack(side="left", padx=(2, 6))

        # Botón Pantalla Completa
        self.btn_fullscreen = ctk.CTkButton(
            self.hud_frame,
            text="⛶ Pantalla Completa (F11)",
            width=150,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.toggle_fullscreen
        )
        self.btn_fullscreen.pack(side="left", padx=4)

        # Botón Salir / Cerrar
        self.btn_close = ctk.CTkButton(
            self.hud_frame,
            text="✕ Salir",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._on_closing
        )
        self.btn_close.pack(side="left", padx=(4, 15))

    def _on_mouse_wheel(self, event: Any) -> None:
        """
        Ajusta el zoom / escala de campo de visión usando la rueda del ratón.
        """
        delta = getattr(event, "delta", 0)
        if delta > 0:
            self.adjust_zoom(0.05)
        elif delta < 0:
            self.adjust_zoom(-0.05)

    def adjust_zoom(self, delta: float) -> None:
        """
        Aumenta o disminuye la escala de campo de visión en vivo.
        """
        new_scale = max(0.50, min(1.50, round(self.content_scale + delta, 2)))
        self.set_zoom(new_scale)

    def set_zoom(self, scale: float) -> None:
        """
        Establece la escala de zoom y actualiza el indicador en el HUD flotante.
        """
        self.content_scale = max(0.50, min(1.50, round(scale, 2)))
        pct = int(round(self.content_scale * 100))
        if hasattr(self, "lbl_hud_zoom"):
            self.lbl_hud_zoom.configure(text=f"🔍 {pct}%")
        self._show_hud()
        self._schedule_hud_hide()

    def _on_hud_template_changed(self, choice: str) -> None:
        """
        Cambia la plantilla óptica sobre la marcha sin pausar la transmisión.
        """
        if "Completo" in choice or "100%" in choice:
            self.aspect_mode = "original"
            self.fit_mode = "fit"
            self.corner_radius_pct = 0.15
            self.margin_pct = 0.04
            self.center_gap_pct = 0.04
            self.set_zoom(0.95)
        elif "VR180" in choice:
            self.aspect_mode = "1:1"
            self.fit_mode = "crop"
            self.corner_radius_pct = 0.75
            self.margin_pct = 0.03
            self.center_gap_pct = 0.05
            self.set_zoom(1.0)
        elif "Cine" in choice:
            self.aspect_mode = "16:9"
            self.fit_mode = "fit"
            self.corner_radius_pct = 0.25
            self.margin_pct = 0.08
            self.center_gap_pct = 0.06
            self.set_zoom(1.0)
        elif "4:3" in choice:
            self.aspect_mode = "4:3"
            self.fit_mode = "crop"
            self.corner_radius_pct = 0.35
            self.margin_pct = 0.04
            self.center_gap_pct = 0.04
            self.set_zoom(1.0)
        elif "Pantalla Completa" in choice:
            self.aspect_mode = "fill"
            self.fit_mode = "crop"
            self.corner_radius_pct = 0.0
            self.margin_pct = 0.0
            self.center_gap_pct = 0.0
            self.set_zoom(1.0)
        else:
            # VR Shinecon 1:1 por defecto
            self.aspect_mode = "1:1"
            self.fit_mode = "crop"
            self.corner_radius_pct = 0.45
            self.margin_pct = 0.04
            self.center_gap_pct = 0.04
            self.set_zoom(1.0)

    def toggle_fullscreen(self) -> None:
        """
        Alterna entre el modo de ventana convencional y Pantalla Completa Sin Bordes,
        respetando el monitor actual (por ejemplo, Spacedesk o pantallas secundarias en el celular).
        """
        self.is_fullscreen = not self.is_fullscreen

        if sys.platform == "win32":
            self._toggle_fullscreen_win32()
        else:
            self.attributes("-fullscreen", self.is_fullscreen)

        if self.is_fullscreen:
            self.btn_fullscreen.configure(text="✕ Salir de Pantalla Completa")
            self.focus_force()
        else:
            self.btn_fullscreen.configure(text="⛶ Pantalla Completa (F11)")

        self._show_hud()
        self._schedule_hud_hide()

    def _toggle_fullscreen_win32(self) -> None:
        """
        Implementa pantalla completa sin bordes en el monitor específico donde se encuentre
        la ventana actualmente, evitando que Windows la devuelva a la pantalla principal (Spacedesk).
        """
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.wm_frame(), 16)

            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            WS_SYSMENU = 0x00080000
            SWP_FRAMECHANGED = 0x0020
            SWP_SHOWWINDOW = 0x0040
            HWND_TOP = 0

            if self.is_fullscreen:
                # 1. Guardamos la posición y dimensiones antes de maximizar
                self._saved_geometry = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
                self._saved_style = user32.GetWindowLongW(hwnd, GWL_STYLE)

                # 2. Obtenemos el punto central actual de la ventana
                center_x = self.winfo_rootx() + max(1, self.winfo_width()) // 2
                center_y = self.winfo_rooty() + max(1, self.winfo_height()) // 2

                class POINT(ctypes.Structure):
                    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

                class RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', wintypes.DWORD),
                        ('rcMonitor', RECT),
                        ('rcWork', RECT),
                        ('dwFlags', wintypes.DWORD)
                    ]

                # 3. Consultamos la información del monitor exacto donde está la ventana (ej. Spacedesk en celular)
                pt = POINT(center_x, center_y)
                hmon = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST = 2
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                user32.GetMonitorInfoW(hmon, ctypes.byref(mi))

                mon_x = mi.rcMonitor.left
                mon_y = mi.rcMonitor.top
                mon_w = mi.rcMonitor.right - mi.rcMonitor.left
                mon_h = mi.rcMonitor.bottom - mi.rcMonitor.top

                # 4. Eliminamos barra de título y bordes de ventana
                new_style = self._saved_style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
                user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)

                # 5. Expandimos a pantalla completa exacta en ese monitor específico
                user32.SetWindowPos(hwnd, HWND_TOP, mon_x, mon_y, mon_w, mon_h, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
            else:
                # Restauramos estilo de ventana estándar y dimensiones previas
                if hasattr(self, "_saved_style"):
                    user32.SetWindowLongW(hwnd, GWL_STYLE, self._saved_style)

                if hasattr(self, "_saved_geometry"):
                    gx, gy, gw, gh = self._saved_geometry
                    user32.SetWindowPos(hwnd, HWND_TOP, gx, gy, gw, gh, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                else:
                    self.attributes("-fullscreen", False)
        except Exception:
            # Fallback seguro
            self.attributes("-fullscreen", self.is_fullscreen)

    def toggle_pause(self) -> None:
        """
        Pausa o reanuda la captura en vivo.
        """
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="▶ Reanudar", fg_color="#16a34a", hover_color="#15803d")
            self.lbl_hud_fps.configure(text="⏸ EN PAUSA", text_color="#f59e0b")
        else:
            self.btn_pause.configure(text="⏸ Pausar", fg_color="#334155", hover_color="#475569")
            self.lbl_hud_fps.configure(text="🔴 EN VIVO", text_color="#22c55e")

    def _on_escape(self) -> None:
        """
        Al presionar la tecla Esc, sale de pantalla completa; si ya está en ventana, cierra la proyección.
        """
        if self.is_fullscreen:
            self.toggle_fullscreen()
        else:
            self._on_closing()

    def _on_mouse_move(self, event: Any) -> None:
        """
        Muestra la barra HUD al detectar movimiento del cursor y reinicia el temporizador.
        """
        self._show_hud()
        self._schedule_hud_hide()

    def _show_hud(self) -> None:
        """
        Hace visible la barra de herramientas HUD.
        """
        self.hud_frame.place(relx=0.5, rely=0.04, anchor="n")

    def _hide_hud(self) -> None:
        """
        Oculta los controles HUD para una experiencia visual totalmente limpia.
        """
        self.hud_frame.place_forget()

    def _schedule_hud_hide(self) -> None:
        """
        Programa la desaparición automática del HUD tras 2.5 segundos de inactividad.
        """
        if self._hud_hide_timer:
            self.after_cancel(self._hud_hide_timer)
        self._hud_hide_timer = self.after(2500, self._hide_hud)

    def apply_template(self, template_id: str) -> None:
        """
        Aplica los parámetros de una plantilla a la proyección en vivo.
        """
        if template_id in LensMaskGenerator.PRESET_TEMPLATES:
            tmpl = LensMaskGenerator.PRESET_TEMPLATES[template_id]
            self.template_id = tmpl.id
            self.aspect_mode = tmpl.aspect_mode
            self.fit_mode = tmpl.fit_mode
            self.corner_radius_pct = tmpl.corner_radius_pct
            self.margin_pct = tmpl.margin_pct
            self.center_gap_pct = tmpl.center_gap_pct
            self.set_zoom(tmpl.content_scale)
            if hasattr(self, "opt_hud_template"):
                if template_id == "virtual_cinema_full":
                    self.opt_hud_template.set("Cine Completo (100% Contenido)")
                elif template_id == "vr180_lens_mask":
                    self.opt_hud_template.set("VR180 Máscara")
                elif template_id == "virtual_cinema_16_9":
                    self.opt_hud_template.set("Cine 16:9")
                elif template_id == "classic_optical_4_3":
                    self.opt_hud_template.set("Formato 4:3")
                elif template_id == "half_sbs_fullscreen":
                    self.opt_hud_template.set("Pantalla Completa")
                else:
                    self.opt_hud_template.set("VR Shinecon (1:1)")

    def _capture_and_stream_loop(self) -> None:
        """
        Bucle de captura a alta velocidad, composición de máscara óptica y emisión.
        """
        frame_interval = 1.0 / max(15, min(self.target_fps, 60))

        while self._is_running:
            start_loop = time.time()

            if not self.is_paused:
                # 1. Captura del fotograma original
                if self.source_type == "window":
                    raw_frame = self.capture_engine.capture_window(self.source_id)
                else:
                    raw_frame = self.capture_engine.capture_monitor(self.source_id)

                if raw_frame is not None and self._is_running:
                    # 2. Composición estereoscópica SBS con esquinas redondeadas y escala FOV
                    target_w = 1280
                    target_h = 720

                    sbs_frame = LensMaskGenerator.compose_preview_sbs(
                        source_frame=raw_frame,
                        target_canvas_w=target_w,
                        target_canvas_h=target_h,
                        aspect_mode=self.aspect_mode,
                        fit_mode=self.fit_mode,
                        corner_radius_pct=self.corner_radius_pct,
                        margin_pct=self.margin_pct,
                        center_gap_pct=self.center_gap_pct,
                        parallax_px=self.parallax_px,
                        content_scale=self.content_scale
                    )

                    # 3. Transmisión al servidor web móvil si está activo
                    if self.stream_server and self.stream_server.is_running():
                        self.stream_server.update_frame(sbs_frame, quality=75)

                    # 4. Envío al hilo de Tkinter para despliegue en pantalla
                    if self._is_running:
                        self.after(0, lambda f=sbs_frame: self._update_display(f))

                    # 5. Cálculo de FPS
                    self.fps_counter += 1
                    now = time.time()
                    if now - self.last_fps_time >= 1.0:
                        self.current_fps = round(self.fps_counter / (now - self.last_fps_time), 1)
                        self.fps_counter = 0
                        self.last_fps_time = now
                        if self._is_running:
                            self.after(0, lambda fps=self.current_fps: self._update_fps_label(fps))

            # Control de tasa de cuadros (cadencia suave)
            elapsed = time.time() - start_loop
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

    def _update_display(self, frame: Image.Image) -> None:
        """
        Escala y coloca la imagen estereoscópica en la etiqueta de la ventana.
        """
        if not self._is_running:
            return
        try:
            if not self.winfo_exists():
                return
            win_w = max(100, self.winfo_width())
            win_h = max(100, self.winfo_height())

            img_w, img_h = frame.size
            ratio = min(win_w / img_w, win_h / img_h)
            disp_w = max(40, int(img_w * ratio))
            disp_h = max(30, int(img_h * ratio))

            ctk_img = ctk.CTkImage(light_image=frame, dark_image=frame, size=(disp_w, disp_h))
            self.lbl_canvas.configure(image=ctk_img)
            self.lbl_canvas.image = ctk_img
        except Exception:
            pass

    def _update_fps_label(self, fps: float) -> None:
        """
        Actualiza el contador numérico de FPS en el HUD de forma segura.
        """
        if not self._is_running:
            return
        try:
            if not self.winfo_exists():
                return
            status_txt = "⏸ EN PAUSA" if self.is_paused else f"🔴 EN VIVO  |  FPS: {fps}"
            self.lbl_hud_fps.configure(text=status_txt)
        except Exception:
            pass

    def _on_closing(self) -> None:
        """
        Detiene los hilos y cierra la ventana de proyección de forma limpia.
        """
        self._is_running = False
        if self._hud_hide_timer:
            try:
                self.after_cancel(self._hud_hide_timer)
            except Exception:
                pass
        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
