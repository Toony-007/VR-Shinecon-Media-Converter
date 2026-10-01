# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: config/config_manager.py
# DESCRIPCIÓN: Gestor centralizado de configuración y persistencia de preferencias.
#              Maneja lectura/escritura en JSON y creación automática de carpetas.
# ==============================================================================

import os
import json
import logging
from typing import Any, Dict

# Configuración básica del registrador de eventos (logging)
logger = logging.getLogger("VRShinecon.Config")


class ConfigManager:
    """
    Clase responsable de gestionar la configuración persistente de la aplicación.
    Guarda y recupera parámetros del usuario desde un archivo JSON local,
    garantizando valores por defecto ante ausencias o corrupciones de datos.
    """

    # Nombre del archivo de configuración por defecto
    CONFIG_FILENAME = "config.json"

    def __init__(self, config_path: str = None) -> None:
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_path (str, opcional): Ruta absoluta o relativa al archivo config.json.
                                         Si no se especifica, se ubica junto a la app.
        """
        # Si no se provee ruta, usamos la misma carpeta del script en ejecución
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, self.CONFIG_FILENAME)
        else:
            self.config_path = config_path

        # Obtenemos la ruta por defecto para las exportaciones en Documentos o Escritorio
        default_export_dir = self._resolve_default_export_dir()

        # Diccionario con valores iniciales seguros y óptimos para VR Shinecon
        self.default_settings: Dict[str, Any] = {
            "language": "es",                        # Idioma inicial ('es' = Español, 'en' = Inglés)
            "theme": "Dark",                         # Tema visual ('Dark', 'Light', 'System')
            "export_directory": default_export_dir,  # Carpeta de salida para medios convertidos
            "default_mode": "auto",                  # Modo inicial ('auto' = Automático, 'custom' = Personalizado)
            "default_crf": 18,                       # Nivel de calidad por defecto (18 = Alta fidelidad visual)
            "default_sbs_mode": "half",              # Tipo SBS ('half' = Half SBS 1080p, 'full' = Full SBS)
            "default_resolution": "1080p",           # Resolución objetivo ('original', '720p', '1080p', '1440p', '4k')
            "default_container": "mp4",              # Contenedor de salida ('mp4', 'mkv')
            "default_encoder": "cpu",                # Codificador ('cpu' libx264, 'nvenc', 'qsv', 'amf')
            "parallax_depth": 0,                     # Desplazamiento horizontal para simulación 3D (0 a 30 px)
            "audio_codec": "copy",                   # Manejo de audio ('copy' directo o 'aac' re-codificado)
            "notify_on_complete": True               # Notificar sonoramente o visualmente al culminar
        }

        # Estructura de datos en memoria para almacenar las opciones cargadas
        self.settings: Dict[str, Any] = {}

        # Cargamos las configuraciones existentes o creamos las predeterminadas
        self.load()

        # Garantizamos que el directorio de salida exista en el disco
        self.ensure_export_directory()

    def _resolve_default_export_dir(self) -> str:
        """
        Determina la ruta recomendada para guardar los videos e imágenes exportadas.
        Prioriza la carpeta 'Documentos' del usuario; si no existe, recurre al 'Escritorio'.
        
        Returns:
            str: Ruta absoluta a la carpeta 'VR_Shinecon_Exports'.
        """
        # Obtenemos la ruta del directorio home del usuario actual
        user_home = os.path.expanduser("~")

        # Candidato principal: Documentos/VR_Shinecon_Exports
        docs_candidate = os.path.join(user_home, "Documents", "VR_Shinecon_Exports")
        
        # Candidato secundario en caso de sistemas con nombres en español 'Mis Documentos'
        docs_es_candidate = os.path.join(user_home, "Mis Documentos", "VR_Shinecon_Exports")

        # Candidato de respaldo: Escritorio/VR_Shinecon_Exports
        desktop_candidate = os.path.join(user_home, "Desktop", "VR_Shinecon_Exports")

        # Verificamos si existe la carpeta Documents
        docs_parent = os.path.join(user_home, "Documents")
        if os.path.exists(docs_parent):
            return docs_candidate
        
        docs_es_parent = os.path.join(user_home, "Mis Documentos")
        if os.path.exists(docs_es_parent):
            return docs_es_candidate

        # Si ninguna existe, usamos Escritorio o el directorio del usuario directamente
        if os.path.exists(os.path.join(user_home, "Desktop")):
            return desktop_candidate
        
        return os.path.join(user_home, "VR_Shinecon_Exports")

    def load(self) -> Dict[str, Any]:
        """
        Carga las configuraciones desde el archivo JSON en disco.
        Si el archivo no existe o está dañado, aplica los valores por defecto y lo guarda.
        
        Returns:
            Dict[str, Any]: Diccionario con las opciones vigentes.
        """
        # Comprobamos si el archivo existe físicamente
        if not os.path.exists(self.config_path):
            logger.info("Archivo de configuración no encontrado. Creando valores por defecto.")
            self.settings = dict(self.default_settings)
            self.save()
            return self.settings

        try:
            # Abrimos el archivo JSON en modo lectura con codificación UTF-8
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Combinamos los valores leídos con los defaults para cubrir claves nuevas si hubo actualización
            self.settings = dict(self.default_settings)
            self.settings.update(data)
            logger.info("Configuraciones cargadas exitosamente desde %s", self.config_path)

        except (json.JSONDecodeError, OSError) as error:
            # En caso de corrupción del JSON, no detenemos el programa; restauramos defaults
            logger.warning("Error leyendo %s (%s). Restaurando configuración predeterminada.", self.config_path, error)
            self.settings = dict(self.default_settings)
            self.save()

        return self.settings

    def save(self) -> bool:
        """
        Escribe las configuraciones vigentes en el archivo JSON.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso de error.
        """
        try:
            # Nos aseguramos de que el directorio padre del archivo exista
            parent_dir = os.path.dirname(self.config_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # Escribimos con indentación legible y preservando caracteres especiales
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info("Configuración guardada satisfactoriamente.")
            return True

        except OSError as error:
            logger.error("No se pudo guardar la configuración en %s: %s", self.config_path, error)
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene el valor de una clave de configuración.
        
        Args:
            key (str): Nombre de la propiedad requerida.
            default (Any, opcional): Valor de reemplazo si no existe la clave.
            
        Returns:
            Any: El valor almacenado o el valor de respaldo.
        """
        return self.settings.get(key, self.default_settings.get(key, default))

    def set(self, key: str, value: Any, auto_save: bool = False) -> None:
        """
        Actualiza el valor de una clave en memoria, con opción de autoguardado.
        
        Args:
            key (str): Nombre de la propiedad a modificar.
            value (Any): Nuevo valor asignado.
            auto_save (bool): Si es True, persiste inmediatamente en el archivo JSON.
        """
        self.settings[key] = value
        if auto_save:
            self.save()

    def ensure_export_directory(self) -> str:
        """
        Verifica que el directorio de exportación configurado exista en el sistema de archivos.
        Si no existe, intenta crearlo automáticamente.
        
        Returns:
            str: Ruta absoluta verificada del directorio de exportación.
        """
        export_dir = self.get("export_directory", self.default_settings["export_directory"])
        try:
            if not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
                logger.info("Directorio de exportación creado: %s", export_dir)
        except OSError as error:
            logger.error("No se pudo crear el directorio de exportación %s: %s", export_dir, error)
            # Como salvaguarda, reasignamos a una carpeta local en la raíz del proyecto
            fallback_dir = os.path.join(os.path.dirname(self.config_path), "VR_Shinecon_Exports")
            os.makedirs(fallback_dir, exist_ok=True)
            self.settings["export_directory"] = fallback_dir
            return fallback_dir

        return export_dir
