# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/tab_settings.py
# DESCRIPCIÓN: Pestaña de configuración de preferencias del usuario, directorios,
#              calidad por defecto, idioma y tema visual.
# ==============================================================================

import os
import subprocess
import tkinter.filedialog as filedialog
import customtkinter as ctk
from typing import Callable, Any

from config.config_manager import ConfigManager
from core.localization import LocalizationManager
from ui.dialogs import ModernMessageDialog


class SettingsTab(ctk.CTkFrame):
    """
    Componente visual que encapsula los controles de configuración persistente.
    Permite modificar rutas de guardado, idioma, temas visuales y calidad por omisión.
    """

    def __init__(
        self,
        parent: Any,
        config_mgr: ConfigManager,
        loc_mgr: LocalizationManager,
        on_theme_change: Callable[[str], None],
        on_language_change: Callable[[str], None]
    ) -> None:
        """
        Inicializa la vista de configuración.
        
        Args:
            parent (Any): Contenedor padre de CustomTkinter.
            config_mgr (ConfigManager): Gestor de persistencia.
            loc_mgr (LocalizationManager): Gestor de traducciones.
            on_theme_change (Callable[[str], None]): Callback para aplicar el tema visual.
            on_language_change (Callable[[str], None]): Callback para aplicar el idioma.
        """
        super().__init__(parent, fg_color="transparent")

        self.config_mgr = config_mgr
        self.loc_mgr = loc_mgr
        self.on_theme_change = on_theme_change
        self.on_language_change = on_language_change

        # Registramos observador para actualizar textos cuando cambie el idioma
        self.loc_mgr.add_listener(self._update_ui_texts)

        # Construcción de la interfaz de la pestaña
        self._build_ui()

    def _build_ui(self) -> None:
        """
        Crea y posiciona todos los elementos visuales utilizando el sistema Grid.
        """
        # Configuramos pesos de columnas para diseño responsivo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Contenedor desplazable para garantizar legibilidad en cualquier resolución
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Tarjeta 1: Directorio de Exportación
        self.dir_card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.dir_card.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.dir_card.grid_columnconfigure(0, weight=1)

        self.lbl_export_dir = ctk.CTkLabel(
            self.dir_card,
            text=self.loc_mgr.t("label_export_dir"),
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_export_dir.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        # Contenedor horizontal para la ruta y botones
        dir_controls_frame = ctk.CTkFrame(self.dir_card, fg_color="transparent")
        dir_controls_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        dir_controls_frame.grid_columnconfigure(0, weight=1)

        current_export_dir = self.config_mgr.get("export_directory", "")
        self.entry_export_dir = ctk.CTkEntry(
            dir_controls_frame,
            font=ctk.CTkFont(size=12),
            height=36
        )
        self.entry_export_dir.insert(0, current_export_dir)
        self.entry_export_dir.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            dir_controls_frame,
            text=self.loc_mgr.t("btn_browse"),
            width=110,
            height=36,
            command=self._on_browse_directory
        )
        self.btn_browse.grid(row=0, column=1, padx=(0, 5))

        self.btn_open_folder = ctk.CTkButton(
            dir_controls_frame,
            text=self.loc_mgr.t("btn_open_folder"),
            width=120,
            height=36,
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_open_export_folder
        )
        self.btn_open_folder.grid(row=0, column=2)

        # Tarjeta 2: Calidad por Defecto (CRF)
        self.quality_card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.quality_card.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.quality_card.grid_columnconfigure(0, weight=1)

        self.lbl_default_crf = ctk.CTkLabel(
            self.quality_card,
            text=self.loc_mgr.t("label_default_crf"),
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_default_crf.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        crf_val = self.config_mgr.get("default_crf", 18)
        self.lbl_crf_val = ctk.CTkLabel(
            self.quality_card,
            text=f"CRF: {crf_val} (Recomendado para VR)",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_crf_val.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))

        self.slider_crf = ctk.CTkSlider(
            self.quality_card,
            from_=14,
            to=28,
            number_of_steps=14,
            command=self._on_crf_slider_change
        )
        self.slider_crf.set(crf_val)
        self.slider_crf.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Tarjeta 3: Apariencia e Idioma
        self.prefs_card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.prefs_card.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.prefs_card.grid_columnconfigure((0, 1), weight=1)

        # Selector de Idioma
        self.lbl_language = ctk.CTkLabel(
            self.prefs_card,
            text=self.loc_mgr.t("label_language"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_language.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        cur_lang = self.config_mgr.get("language", "es")
        lang_display = "Español" if cur_lang == "es" else "English"
        self.opt_language = ctk.CTkOptionMenu(
            self.prefs_card,
            values=["Español", "English"],
            command=self._on_language_selected,
            height=34
        )
        self.opt_language.set(lang_display)
        self.opt_language.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Selector de Tema
        self.lbl_theme = ctk.CTkLabel(
            self.prefs_card,
            text=self.loc_mgr.t("label_theme"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_theme.grid(row=0, column=1, sticky="w", padx=15, pady=(15, 5))

        cur_theme = self.config_mgr.get("theme", "Dark")
        theme_map = {"Dark": self.loc_mgr.t("theme_dark"), "Light": self.loc_mgr.t("theme_light"), "System": self.loc_mgr.t("theme_system")}
        self.opt_theme = ctk.CTkOptionMenu(
            self.prefs_card,
            values=[self.loc_mgr.t("theme_dark"), self.loc_mgr.t("theme_light"), self.loc_mgr.t("theme_system")],
            command=self._on_theme_selected,
            height=34
        )
        self.opt_theme.set(theme_map.get(cur_theme, self.loc_mgr.t("theme_dark")))
        self.opt_theme.grid(row=1, column=1, sticky="ew", padx=15, pady=(0, 15))

        # Botón Guardar Cambios
        self.btn_save = ctk.CTkButton(
            self.scroll_frame,
            text=self.loc_mgr.t("btn_save_settings"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self._on_save_settings
        )
        self.btn_save.grid(row=3, column=0, sticky="ew", padx=10, pady=20)

    def _on_browse_directory(self) -> None:
        """
        Abre el explorador de archivos nativo para seleccionar la carpeta de destino.
        """
        current = self.entry_export_dir.get().strip() or os.path.expanduser("~")
        chosen = filedialog.askdirectory(initialdir=current, title=self.loc_mgr.t("label_export_dir"))
        if chosen:
            self.entry_export_dir.delete(0, "end")
            self.entry_export_dir.insert(0, chosen)

    def _on_open_export_folder(self) -> None:
        """
        Abre la carpeta de exportación en el explorador de archivos del sistema operativo.
        """
        folder_path = self.entry_export_dir.get().strip()
        if folder_path and os.path.exists(folder_path):
            try:
                if os.name == "nt":
                    os.startfile(folder_path)
                else:
                    subprocess.Popen(["xdg-open", folder_path])
            except Exception as ex:
                ModernMessageDialog(self.winfo_toplevel(), self.loc_mgr.t("dialog_error_title"), str(ex), "error")
        else:
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_warning_title"),
                f"La carpeta '{folder_path}' aún no existe en disco.",
                "warning"
            )

    def _on_crf_slider_change(self, value: float) -> None:
        """
        Maneja el evento de desplazamiento del control de calidad.
        """
        crf_int = int(round(value))
        if crf_int <= 17:
            desc = "Calidad Extrema (Archivos más pesados)"
        elif crf_int <= 20:
            desc = "Alta Nitidez (Óptimo VR)"
        elif crf_int <= 23:
            desc = "Equilibrado Estándar"
        else:
            desc = "Mayor Compresión (Menor peso)"
        self.lbl_crf_val.configure(text=f"CRF: {crf_int} - {desc}")

    def _on_language_selected(self, choice: str) -> None:
        """
        Aplica el cambio de idioma cuando el usuario selecciona una opción en el menú.
        """
        new_lang = "es" if choice == "Español" else "en"
        self.on_language_change(new_lang)

    def _on_theme_selected(self, choice: str) -> None:
        """
        Aplica el cambio de tema de CustomTkinter.
        """
        if choice in [self.loc_mgr.t("theme_dark"), "Modo Oscuro", "Dark Mode"]:
            theme_key = "Dark"
        elif choice in [self.loc_mgr.t("theme_light"), "Modo Claro", "Light Mode"]:
            theme_key = "Light"
        else:
            theme_key = "System"

        self.on_theme_change(theme_key)

    def _on_save_settings(self) -> None:
        """
        Persiste los datos de configuración en config.json y muestra confirmación visual.
        """
        # Actualizamos valores en el gestor
        export_path = self.entry_export_dir.get().strip()
        crf_val = int(round(self.slider_crf.get()))
        lang_code = "es" if self.opt_language.get() == "Español" else "en"

        theme_txt = self.opt_theme.get()
        if "Oscuro" in theme_txt or "Dark" in theme_txt:
            theme_code = "Dark"
        elif "Claro" in theme_txt or "Light" in theme_txt:
            theme_code = "Light"
        else:
            theme_code = "System"

        self.config_mgr.set("export_directory", export_path)
        self.config_mgr.set("default_crf", crf_val)
        self.config_mgr.set("language", lang_code)
        self.config_mgr.set("theme", theme_code)

        # Guardamos en disco
        if self.config_mgr.save():
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_success_title"),
                self.loc_mgr.t("settings_saved_msg"),
                "success"
            )
        else:
            ModernMessageDialog(
                self.winfo_toplevel(),
                self.loc_mgr.t("dialog_error_title"),
                "No se pudo guardar el archivo de configuración.",
                "error"
            )

    def _update_ui_texts(self, lang_code: str) -> None:
        """
        Actualiza dinámicamente todos los rótulos y botones de la pestaña al cambiar el idioma.
        """
        self.lbl_export_dir.configure(text=self.loc_mgr.t("label_export_dir"))
        self.btn_browse.configure(text=self.loc_mgr.t("btn_browse"))
        self.btn_open_folder.configure(text=self.loc_mgr.t("btn_open_folder"))
        self.lbl_default_crf.configure(text=self.loc_mgr.t("label_default_crf"))
        self.lbl_language.configure(text=self.loc_mgr.t("label_language"))
        self.lbl_theme.configure(text=self.loc_mgr.t("label_theme"))
        self.btn_save.configure(text=self.loc_mgr.t("btn_save_settings"))

        # Actualizamos opciones del menú de tema
        current_theme = self.config_mgr.get("theme", "Dark")
        theme_names = [self.loc_mgr.t("theme_dark"), self.loc_mgr.t("theme_light"), self.loc_mgr.t("theme_system")]
        self.opt_theme.configure(values=theme_names)
        if current_theme == "Dark":
            self.opt_theme.set(self.loc_mgr.t("theme_dark"))
        elif current_theme == "Light":
            self.opt_theme.set(self.loc_mgr.t("theme_light"))
        else:
            self.opt_theme.set(self.loc_mgr.t("theme_system"))
