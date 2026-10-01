# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/app.py
# DESCRIPCIÓN: Ventana principal de la aplicación construida con CustomTkinter.
#              Orquesta las pestañas de navegación (Tabview), el interruptor de
#              modo oscuro, el selector de idioma y el ciclo de vida del programa.
# ==============================================================================

import os
import sys
import customtkinter as ctk
from typing import Optional

from config.config_manager import ConfigManager
from core.localization import LocalizationManager
from core.media_processor import MediaProcessor
from ui.tab_conversion import ConversionTab
from ui.tab_streaming import StreamingTab
from ui.tab_settings import SettingsTab
from ui.tab_info import InfoTab
from ui.dialogs import ModernMessageDialog, ModernConfirmDialog


class App(ctk.CTk):
    """
    Clase principal de la aplicación de escritorio.
    Hereda de customtkinter.CTk y gestiona la ventana raíz, temas visuales,
    sistema multilingüe e integración de pestañas.
    """

    APP_VERSION = "1.0.0"

    def __init__(self, config_mgr: ConfigManager) -> None:
        """
        Inicializa la ventana principal y los subsistemas.
        
        Args:
            config_mgr (ConfigManager): Gestor de configuración persistente.
        """
        super().__init__()

        self.config_mgr = config_mgr

        # Inicializamos el gestor de traducciones con el idioma guardado
        saved_lang = self.config_mgr.get("language", "es")
        self.loc_mgr = LocalizationManager(current_language=saved_lang)

        # Inicializamos el motor FFmpeg
        self.processor = MediaProcessor()

        # Configuramos tema visual inicial (por defecto Dark)
        saved_theme = self.config_mgr.get("theme", "Dark")
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("blue")

        # Configuración dimensional y responsiva de la ventana
        self.title(self.loc_mgr.t("app_title"))
        self.geometry("1020x720")
        self.minsize(880, 600)

        # Configuración del sistema de rejilla (Grid) con pesos (weight)
        # Fila 0: Barra superior (header)
        # Fila 1: Pestañas de contenido (tabview, expande verticalmente)
        # Fila 2: Barra de estado inferior (status bar)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Construcción de la interfaz
        self._build_header()
        self._build_tabview()
        self._build_statusbar()

        # Suscripción a cambios de idioma
        self.loc_mgr.add_listener(self._on_language_updated)

        # Verificación inicial de dependencias externas (FFmpeg)
        self.after(300, self._check_dependencies_on_startup)

        # Protocolo para intercepción del cierre de ventana
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _build_header(self) -> None:
        """
        Crea la barra superior con el logotipo, título y controles de acceso rápido (tema e idioma).
        """
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#e2e8f0", "#1e293b"), height=64)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Subcontenedor izquierdo: Título e ícono
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        self.lbl_app_title = ctk.CTkLabel(
            title_box,
            text="👓 VR Shinecon Media Converter",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_app_title.pack(side="left", padx=(0, 10))

        self.lbl_subtitle = ctk.CTkLabel(
            title_box,
            text=f"|  {self.loc_mgr.t('app_subtitle')}",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_subtitle.pack(side="left")

        # Subcontenedor derecho: Interruptor de modo oscuro y selector rápido de idioma
        controls_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_box.grid(row=0, column=1, sticky="e", padx=20, pady=10)

        # Menú rápido de idioma
        cur_lang = self.loc_mgr.get_language()
        lang_label = "Español" if cur_lang == "es" else "English"
        self.opt_quick_lang = ctk.CTkOptionMenu(
            controls_box,
            values=["Español", "English"],
            width=100,
            height=28,
            command=self._on_quick_lang_changed
        )
        self.opt_quick_lang.set(lang_label)
        self.opt_quick_lang.pack(side="left", padx=(0, 15))

        # Interruptor de Modo Oscuro (requisito estricto: visible para alternar a modo claro)
        is_dark = (ctk.get_appearance_mode().lower() == "dark")
        self.switch_dark_mode = ctk.CTkSwitch(
            controls_box,
            text=self.loc_mgr.t("theme_dark"),
            command=self._on_toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        if is_dark:
            self.switch_dark_mode.select()
        else:
            self.switch_dark_mode.deselect()
        self.switch_dark_mode.pack(side="left")

    def _build_tabview(self) -> None:
        """
        Construye el componente de pestañas (Tabview) y aloja las vistas hijas.
        """
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=15, pady=(10, 5))

        # Nombres de las pestañas
        self.tab_name_conv = self.loc_mgr.t("tab_conversion")
        self.tab_name_stream = self.loc_mgr.t("tab_streaming")
        self.tab_name_sett = self.loc_mgr.t("tab_settings")
        self.tab_name_info = self.loc_mgr.t("tab_info")

        # Añadimos las pestañas al componente Tabview
        self.tabview.add(self.tab_name_conv)
        self.tabview.add(self.tab_name_stream)
        self.tabview.add(self.tab_name_sett)
        self.tabview.add(self.tab_name_info)

        # Configuramos pesos en cada contenedor de pestaña
        self.tabview.tab(self.tab_name_conv).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_name_conv).grid_rowconfigure(0, weight=1)

        self.tabview.tab(self.tab_name_stream).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_name_stream).grid_rowconfigure(0, weight=1)

        self.tabview.tab(self.tab_name_sett).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_name_sett).grid_rowconfigure(0, weight=1)

        self.tabview.tab(self.tab_name_info).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_name_info).grid_rowconfigure(0, weight=1)

        # Instanciamos la Pestaña 1: Conversión (Principal)
        self.view_conversion = ConversionTab(
            parent=self.tabview.tab(self.tab_name_conv),
            config_mgr=self.config_mgr,
            loc_mgr=self.loc_mgr,
            processor=self.processor
        )
        self.view_conversion.grid(row=0, column=0, sticky="nsew")

        # Instanciamos la Pestaña 2: Streaming en Vivo (Tiempo Real)
        self.view_streaming = StreamingTab(
            parent=self.tabview.tab(self.tab_name_stream),
            config_mgr=self.config_mgr,
            loc_mgr=self.loc_mgr
        )
        self.view_streaming.grid(row=0, column=0, sticky="nsew")

        # Instanciamos la Pestaña 3: Configuración (Settings)
        self.view_settings = SettingsTab(
            parent=self.tabview.tab(self.tab_name_sett),
            config_mgr=self.config_mgr,
            loc_mgr=self.loc_mgr,
            on_theme_change=self.apply_theme,
            on_language_change=self.apply_language
        )
        self.view_settings.grid(row=0, column=0, sticky="nsew")

        # Instanciamos la Pestaña 4: Información VR (Guía y Educación)
        self.view_info = InfoTab(
            parent=self.tabview.tab(self.tab_name_info),
            loc_mgr=self.loc_mgr
        )
        self.view_info.grid(row=0, column=0, sticky="nsew")

    def _build_statusbar(self) -> None:
        """
        Crea la barra de estado inferior para mostrar información contextual.
        """
        self.status_frame = ctk.CTkFrame(self, corner_radius=0, height=28, fg_color=("#cbd5e1", "#0f172a"))
        self.status_frame.grid(row=2, column=0, sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.lbl_status_export = ctk.CTkLabel(
            self.status_frame,
            text=f"📁 Salida: {self.config_mgr.get('export_directory')}",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.lbl_status_export.grid(row=0, column=0, sticky="w", padx=15, pady=3)

        ffmpeg_status = "FFmpeg: Listo ✅" if self.processor.is_ffmpeg_installed() else "FFmpeg: No detectado ⚠️"
        self.lbl_status_engine = ctk.CTkLabel(
            self.status_frame,
            text=f"Motor {ffmpeg_status} | Versión {self.APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.lbl_status_engine.grid(row=0, column=1, sticky="e", padx=15, pady=3)

    def _on_toggle_theme(self) -> None:
        """
        Alterna entre modo oscuro y modo claro mediante el interruptor de la barra superior.
        """
        if self.switch_dark_mode.get():
            self.apply_theme("Dark")
        else:
            self.apply_theme("Light")

    def apply_theme(self, theme_mode: str) -> None:
        """
        Aplica el modo visual global y lo guarda en las preferencias.
        
        Args:
            theme_mode (str): 'Dark', 'Light' o 'System'.
        """
        ctk.set_appearance_mode(theme_mode)
        self.config_mgr.set("theme", theme_mode, auto_save=True)

        is_dark = (theme_mode.lower() == "dark")
        if is_dark:
            self.switch_dark_mode.select()
        else:
            self.switch_dark_mode.deselect()

    def _on_quick_lang_changed(self, choice: str) -> None:
        """
        Maneja el selector de idioma de la barra superior.
        """
        new_lang = "es" if choice == "Español" else "en"
        self.apply_language(new_lang)

    def apply_language(self, language_code: str) -> None:
        """
        Aplica el cambio de idioma a toda la aplicación de forma dinámica e instantánea.
        
        Args:
            language_code (str): 'es' o 'en'.
        """
        self.loc_mgr.set_language(language_code)
        self.config_mgr.set("language", language_code, auto_save=True)

    def _on_language_updated(self, lang_code: str) -> None:
        """
        Callback ejecutada cuando el gestor de localización notifica un cambio de idioma.
        """
        self.title(self.loc_mgr.t("app_title"))
        self.lbl_subtitle.configure(text=f"|  {self.loc_mgr.t('app_subtitle')}")
        self.switch_dark_mode.configure(text=self.loc_mgr.t("theme_dark"))

        lang_label = "Español" if lang_code == "es" else "English"
        self.opt_quick_lang.set(lang_label)
        self.lbl_status_export.configure(text=f"📁 Salida: {self.config_mgr.get('export_directory')}")

        # Actualizamos dinámicamente los textos de los botones de pestañas en el Tabview
        try:
            btn_dict = getattr(self.tabview._segmented_button, "_buttons_dict", {})
            if self.tab_name_conv in btn_dict:
                btn_dict[self.tab_name_conv].configure(text=self.loc_mgr.t("tab_conversion"))
            if self.tab_name_stream in btn_dict:
                btn_dict[self.tab_name_stream].configure(text=self.loc_mgr.t("tab_streaming"))
            if self.tab_name_sett in btn_dict:
                btn_dict[self.tab_name_sett].configure(text=self.loc_mgr.t("tab_settings"))
            if self.tab_name_info in btn_dict:
                btn_dict[self.tab_name_info].configure(text=self.loc_mgr.t("tab_info"))
        except Exception:
            pass

    def _check_dependencies_on_startup(self) -> None:
        """
        Comprueba la instalación de FFmpeg al iniciar la aplicación.
        Si no se detecta, despliega una ventana modal explicativa.
        """
        if not self.processor.is_ffmpeg_installed():
            ModernMessageDialog(
                self,
                self.loc_mgr.t("ffmpeg_missing_title"),
                self.loc_mgr.t("ffmpeg_missing_msg"),
                "error"
            )

    def _on_window_close(self) -> None:
        """
        Maneja el evento de cierre de la ventana, deteniendo tareas en segundo plano
        y liberando sockets de red del servidor de streaming.
        """
        # Detenemos de forma segura el servidor web local y proyecciones de streaming
        try:
            if hasattr(self, "view_streaming"):
                self.view_streaming.stop_all()
        except Exception:
            pass

        if self.view_conversion.is_converting:
            confirm = ModernConfirmDialog(
                self,
                self.loc_mgr.t("confirm_title"),
                "Hay conversiones de medios en ejecución. ¿Deseas detenerlas y salir?",
                self.loc_mgr.t("btn_yes"),
                self.loc_mgr.t("btn_no")
            )
            if not confirm.result:
                return
            self.processor.cancel()

        self.destroy()
