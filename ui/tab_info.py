# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: ui/tab_info.py
# DESCRIPCIÓN: Pestaña informativa y educativa con guía técnica sobre el formato
#              Side-by-Side (SBS), ópticas de VR Shinecon y calibración estereoscópica.
# ==============================================================================

import customtkinter as ctk
from typing import Any

from core.localization import LocalizationManager


class InfoTab(ctk.CTkFrame):
    """
    Pestaña que proporciona orientación técnica clara al usuario sobre el uso
    de visores VR pasivos, formatos estereoscópicos y consejos de reproducción.
    """

    def __init__(self, parent: Any, loc_mgr: LocalizationManager) -> None:
        """
        Inicializa la vista de información y guía.
        
        Args:
            parent (Any): Contenedor padre.
            loc_mgr (LocalizationManager): Gestor de traducciones.
        """
        super().__init__(parent, fg_color="transparent")

        self.loc_mgr = loc_mgr

        # Suscribimos la vista para actualizar textos al cambiar el idioma
        self.loc_mgr.add_listener(self._update_ui_texts)

        # Construcción visual
        self._build_ui()

    def _build_ui(self) -> None:
        """
        Estructura el contenido en un contenedor desplazable con tarjetas visuales.
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Tarjeta 1: ¿Qué es Side-by-Side (SBS)?
        self.card_sbs = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.card_sbs.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.card_sbs.grid_columnconfigure(0, weight=1)

        self.lbl_title_sbs = ctk.CTkLabel(
            self.card_sbs,
            text=self.loc_mgr.t("info_title"),
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.lbl_title_sbs.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 8))

        self.lbl_body_sbs = ctk.CTkLabel(
            self.card_sbs,
            text=self.loc_mgr.t("info_body"),
            justify="left",
            wraplength=760,
            font=ctk.CTkFont(size=12)
        )
        self.lbl_body_sbs.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

        # Tarjeta 2: Consejos y Reproductores Recomendados
        self.card_tips = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        self.card_tips.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.card_tips.grid_columnconfigure(0, weight=1)

        self.lbl_tips_title = ctk.CTkLabel(
            self.card_tips,
            text="📱 Reproductores Recomendados para Celulares con VR Shinecon",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_tips_title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 8))

        tips_text = (
            "Para una experiencia cinematográfica óptima con tu visor VR Shinecon:\n\n"
            "1. Android: Utiliza aplicaciones como 'VLC for Android' (activando modo SBS o visor),\n"
            "   'VR Player PRO', 'GizmoVR' o 'AAA VR Cinema'.\n"
            "2. iOS (iPhone): Recomendamos 'VR Player', 'Mobile VR Station' o 'Homido 360 VR Player'.\n"
            "3. Enfoque Mecánico: Ajusta las perillas laterales y superiores de tu VR Shinecon para calibrar\n"
            "   la distancia interpupilar (IPD) y la distancia focal de las lentes de acuerdo a tu vista.\n"
            "4. Centro de Pantalla: Asegúrate de que la línea divisoria central del video Half SBS coincida\n"
            "   con el separador físico central del visor."
        )

        self.lbl_tips_body = ctk.CTkLabel(
            self.card_tips,
            text=tips_text,
            justify="left",
            wraplength=760,
            font=ctk.CTkFont(size=12)
        )
        self.lbl_tips_body.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

    def _update_ui_texts(self, lang_code: str) -> None:
        """
        Actualiza el contenido textual ante cambios de idioma.
        """
        self.lbl_title_sbs.configure(text=self.loc_mgr.t("info_title"))
        self.lbl_body_sbs.configure(text=self.loc_mgr.t("info_body"))
