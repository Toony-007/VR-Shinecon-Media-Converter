# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/dialogs.py
# DESCRIPCIÓN: Ventanas modales y cuadros de diálogo estilizados con CustomTkinter.
#              Ofrece notificaciones de error, advertencias y confirmaciones
#              integradas con el tema visual de la aplicación.
# ==============================================================================

import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Any
import customtkinter as ctk


class ModernMessageDialog(ctk.CTkToplevel):
    """
    Cuadro de diálogo modal estilizado para mostrar mensajes informativos,
    advertencias o errores al usuario sin romper el diseño de CustomTkinter.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        message: str,
        icon_type: str = "info",
        button_text: str = "Aceptar"
    ) -> None:
        """
        Inicializa la ventana modal del diálogo.
        
        Args:
            parent (ctk.CTk): Ventana principal que invoca este modal.
            title (str): Título de la ventana.
            message (str): Texto descriptivo del mensaje.
            icon_type (str): Tipo de ícono ('info', 'warning', 'error', 'success').
            button_text (str): Texto del botón de confirmación.
        """
        super().__init__(parent)

        # Configuración de propiedades de la ventana
        self.title(title)
        self.geometry("460x240")
        self.resizable(False, False)

        # Configuramos comportamiento modal (bloquea la ventana padre)
        self.transient(parent)
        self.grab_set()

        # Paleta de colores distintiva según la categoría del mensaje
        color_badges = {
            "info": ("#1f538d", "ℹ️ INFORMACIÓN"),
            "warning": ("#d97706", "⚠️ ADVERTENCIA"),
            "error": ("#dc2626", "❌ ERROR"),
            "success": ("#16a34a", "✅ ÉXITO")
        }
        badge_color, badge_text = color_badges.get(icon_type, ("#1f538d", "ℹ️ INFORMACIÓN"))

        # Configuración del sistema de rejilla (Grid)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Encabezado con insignia de color
        header_frame = ctk.CTkFrame(self, fg_color=badge_color, corner_radius=0, height=38)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)

        header_label = ctk.CTkLabel(
            header_frame,
            text=badge_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        header_label.pack(side="left", padx=15, pady=6)

        # Contenedor principal del cuerpo del mensaje
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=15)

        msg_label = ctk.CTkLabel(
            body_frame,
            text=message,
            wraplength=410,
            justify="left",
            font=ctk.CTkFont(size=12)
        )
        msg_label.pack(expand=True, fill="both", anchor="w")

        # Botón inferior de confirmación
        btn_action = ctk.CTkButton(
            self,
            text=button_text,
            width=120,
            height=34,
            command=self._on_close
        )
        btn_action.grid(row=2, column=0, pady=(0, 15))

        # Centramos el diálogo respecto a la ventana padre
        self._center_window(parent)

        # Esperamos el cierre de la ventana modal
        self.wait_window()

    def _center_window(self, parent: ctk.CTk) -> None:
        """
        Calcula las coordenadas geométricas para centrar el modal sobre su ventana padre.
        """
        self.update_idletasks()
        try:
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()

            dialog_w = self.winfo_width()
            dialog_h = self.winfo_height()

            pos_x = parent_x + (parent_w - dialog_w) // 2
            pos_y = parent_y + (parent_h - dialog_h) // 2
            self.geometry(f"+{pos_x}+{pos_y}")
        except Exception:
            pass

    def _on_close(self) -> None:
        """
        Libera el foco modal y destruye la ventana.
        """
        self.grab_release()
        self.destroy()


class ModernConfirmDialog(ctk.CTkToplevel):
    """
    Diálogo modal de confirmación con opciones Sí / No.
    Retorna un valor booleano indicando la decisión tomada por el usuario.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        message: str,
        yes_text: str = "Sí",
        no_text: str = "No"
    ) -> None:
        """
        Inicializa el modal de confirmación.
        
        Args:
            parent (ctk.CTk): Ventana padre.
            title (str): Título de la ventana.
            message (str): Pregunta de confirmación.
            yes_text (str): Texto para la opción positiva.
            no_text (str): Texto para la opción negativa.
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("440x220")
        self.resizable(False, False)
        self.result: bool = False

        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Encabezado
        header_frame = ctk.CTkFrame(self, fg_color="#ca8a04", corner_radius=0, height=36)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)

        header_label = ctk.CTkLabel(
            header_frame,
            text="❓ CONFIRMACIÓN",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        header_label.pack(side="left", padx=15, pady=6)

        # Cuerpo del mensaje
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=15)

        msg_label = ctk.CTkLabel(
            body_frame,
            text=message,
            wraplength=390,
            justify="left",
            font=ctk.CTkFont(size=12)
        )
        msg_label.pack(expand=True, fill="both")

        # Contenedor de botones de acción
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, pady=(0, 15))

        btn_yes = ctk.CTkButton(
            buttons_frame,
            text=yes_text,
            width=100,
            height=32,
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self._on_yes
        )
        btn_yes.pack(side="left", padx=10)

        btn_no = ctk.CTkButton(
            buttons_frame,
            text=no_text,
            width=100,
            height=32,
            fg_color="#64748b",
            hover_color="#475569",
            command=self._on_no
        )
        btn_no.pack(side="left", padx=10)

        self._center_window(parent)
        self.wait_window()

    def _center_window(self, parent: ctk.CTk) -> None:
        """
        Centra la ventana respecto al elemento padre.
        """
        self.update_idletasks()
        try:
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()

            pos_x = parent_x + (parent_w - self.winfo_width()) // 2
            pos_y = parent_y + (parent_h - self.winfo_height()) // 2
            self.geometry(f"+{pos_x}+{pos_y}")
        except Exception:
            pass

    def _on_yes(self) -> None:
        """
        Registra afirmación y cierra la ventana.
        """
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_no(self) -> None:
        """
        Registra negación y cierra la ventana.
        """
        self.result = False
        self.grab_release()
        self.destroy()


class ModernPreviewModal(ctk.CTkToplevel):
    """
    Ventana modal estilizada para inspeccionar la vista previa estereoscópica en alta resolución.
    Permite verificar el encaje óptico de esquinas redondeadas y calibración antes de la exportación,
    con soporte completo para Pantalla Completa Sin Bordes (F11, Doble Clic, Esc) para probar
    directamente con el celular montado en las gafas VR.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        preview_image: Any,
        title: str = "Vista Previa Estereoscópica SBS"
    ) -> None:
        """
        Inicializa el modal de vista previa ampliada con soporte de pantalla completa.
        
        Args:
            parent (ctk.CTk): Ventana invocadora.
            preview_image (PIL.Image.Image): Imagen compuesta SBS generada.
            title (str): Título de la ventana.
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("980x620")
        self.minsize(720, 480)
        self.configure(fg_color="#000000")

        self.transient(parent)
        self.grab_set()

        self.preview_image = preview_image
        self.is_fullscreen: bool = False

        # Rejilla principal responsiva
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Barra superior
        self.grid_rowconfigure(1, weight=1)  # Lienzo central
        self.grid_rowconfigure(2, weight=0)  # Barra inferior

        # Barra superior con título
        self.top_frame = ctk.CTkFrame(self, height=40, fg_color=("#1e293b", "#0f172a"), corner_radius=0)
        self.top_frame.grid(row=0, column=0, sticky="ew")
        self.top_frame.grid_propagate(False)

        lbl_top = ctk.CTkLabel(
            self.top_frame,
            text=f"👓 {title} ({preview_image.width}x{preview_image.height})",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        lbl_top.pack(side="left", padx=15, pady=8)

        # Contenedor central de la imagen con fondo negro absoluto
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)

        self.lbl_image = ctk.CTkLabel(self.canvas_frame, text="", fg_color="#000000")
        self.lbl_image.grid(row=0, column=0, sticky="nsew")

        # Notificación sutil flotante en pantalla completa
        self.lbl_toast = ctk.CTkLabel(
            self,
            text="Presiona ESC o F11 para salir de Pantalla Completa",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=8,
            height=28
        )

        # Barra inferior con botones de acción
        self.bottom_frame = ctk.CTkFrame(self, height=44, fg_color="#090d16", corner_radius=0)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        # Indicador de atajo rápido a la izquierda
        lbl_hint = ctk.CTkLabel(
            self.bottom_frame,
            text="💡 Doble clic en la imagen o pulsa F11 para Pantalla Completa sin bordes",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_hint.pack(side="left", padx=15, pady=6)

        btn_close = ctk.CTkButton(
            self.bottom_frame,
            text="Cerrar",
            width=100,
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_close
        )
        btn_close.pack(side="right", padx=(10, 15), pady=6)

        self.btn_fullscreen = ctk.CTkButton(
            self.bottom_frame,
            text="⛶ Pantalla Completa (F11)",
            width=180,
            height=30,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self.toggle_fullscreen
        )
        self.btn_fullscreen.pack(side="right", pady=6)

        # Atajos de teclado y eventos
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._on_escape())
        self.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.lbl_image.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.lbl_image.bind("<Button-1>", lambda e: self.focus_set())
        self.canvas_frame.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.bind("<Configure>", self._on_resize)

        # Enlace a elementos internos de Tkinter para capturar doble clic
        self.after(100, self._bind_internal_events)

        self._toast_timer: Optional[str] = None
        self._center_window(parent)
        self.after(50, lambda: self.focus_force())
        self.after(60, self._render_image)

    def _bind_internal_events(self) -> None:
        """
        Garantiza que el doble clic se capture directamente en el lienzo donde se dibuja la imagen.
        """
        try:
            for child in (getattr(self.lbl_image, "_label", None), getattr(self.lbl_image, "_canvas", None)):
                if child is not None:
                    child.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
                    child.bind("<Button-1>", lambda e: self.focus_set())
        except Exception:
            pass

    def toggle_fullscreen(self) -> None:
        """
        Alterna entre modo ventana estándar y pantalla completa sin bordes
        para calibrar visualmente las dimensiones ópticas en el visor VR,
        respetando el monitor donde esté ubicada (ej. Spacedesk en celular).
        """
        self.is_fullscreen = not self.is_fullscreen

        if sys.platform == "win32":
            self._toggle_fullscreen_win32()
        else:
            self.attributes("-fullscreen", self.is_fullscreen)

        if self.is_fullscreen:
            self.focus_force()
            # Ocultamos barras superior e inferior para vista pura sin bordes
            self.top_frame.grid_remove()
            self.bottom_frame.grid_remove()
            self.canvas_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=0, pady=0)
            
            # Mostramos el indicador flotante de salida
            self.lbl_toast.place(relx=0.5, rely=0.04, anchor="center")
            self._schedule_hide_toast()
        else:
            # Restauramos el modo ventana
            self.lbl_toast.place_forget()
            self.top_frame.grid()
            self.bottom_frame.grid()
            self.canvas_frame.grid(row=1, column=0, rowspan=1, sticky="nsew", padx=10, pady=10)

        # Re-renderizamos ajustando al nuevo tamaño de lienzo
        self.after(50, self._render_image)

    def _toggle_fullscreen_win32(self) -> None:
        """
        Aplica pantalla completa sin bordes en el monitor activo (Spacedesk/secundario).
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
                self._saved_geometry = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
                self._saved_style = user32.GetWindowLongW(hwnd, GWL_STYLE)

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

                pt = POINT(center_x, center_y)
                hmon = user32.MonitorFromPoint(pt, 2)
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                user32.GetMonitorInfoW(hmon, ctypes.byref(mi))

                mon_x = mi.rcMonitor.left
                mon_y = mi.rcMonitor.top
                mon_w = mi.rcMonitor.right - mi.rcMonitor.left
                mon_h = mi.rcMonitor.bottom - mi.rcMonitor.top

                new_style = self._saved_style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
                user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                user32.SetWindowPos(hwnd, HWND_TOP, mon_x, mon_y, mon_w, mon_h, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
            else:
                if hasattr(self, "_saved_style"):
                    user32.SetWindowLongW(hwnd, GWL_STYLE, self._saved_style)

                if hasattr(self, "_saved_geometry"):
                    gx, gy, gw, gh = self._saved_geometry
                    user32.SetWindowPos(hwnd, HWND_TOP, gx, gy, gw, gh, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                else:
                    self.attributes("-fullscreen", False)
        except Exception:
            self.attributes("-fullscreen", self.is_fullscreen)

    def _schedule_hide_toast(self) -> None:
        """
        Oculta automáticamente el aviso flotante tras 2.5 segundos.
        """
        if self._toast_timer:
            self.after_cancel(self._toast_timer)
        self._toast_timer = self.after(2500, lambda: self.lbl_toast.place_forget())

    def _on_escape(self) -> None:
        """
        Maneja la pulsación de la tecla Escape: sale de pantalla completa si está activa,
        o cierra la ventana si ya está en modo ventana.
        """
        if self.is_fullscreen:
            self.toggle_fullscreen()
        else:
            self._on_close()

    def _render_image(self) -> None:
        """
        Escala la imagen para que encaje proporcionalmente en el área disponible.
        """
        try:
            target_w = max(100, self.canvas_frame.winfo_width())
            target_h = max(100, self.canvas_frame.winfo_height())

            img_w, img_h = self.preview_image.size
            ratio = min(target_w / img_w, target_h / img_h)

            display_w = int(img_w * ratio)
            display_h = int(img_h * ratio)

            ctk_img = ctk.CTkImage(
                light_image=self.preview_image,
                dark_image=self.preview_image,
                size=(display_w, display_h)
            )
            self.lbl_image.configure(image=ctk_img)
            self.lbl_image.image = ctk_img
        except Exception:
            pass

    def _on_resize(self, event: Any) -> None:
        """
        Maneja el redimensionamiento de la ventana.
        """
        if event.widget == self:
            self._render_image()

    def _center_window(self, parent: ctk.CTk) -> None:
        """
        Centra la ventana respecto al contenedor padre.
        """
        self.update_idletasks()
        try:
            pos_x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
            pos_y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{pos_x}+{pos_y}")
        except Exception:
            pass

    def _on_close(self) -> None:
        """
        Cierra el modal de vista previa de forma limpia.
        """
        if self.is_fullscreen:
            self.attributes("-fullscreen", False)
        self.grab_release()
        self.destroy()
