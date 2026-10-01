# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: main.py
# DESCRIPCIÓN: Punto de entrada principal (Entry Point) de la aplicación de escritorio.
#              Inicializa el sistema de registro de eventos (logging), carga
#              la configuración y levanta el bucle de eventos principal (mainloop).
# ==============================================================================

import sys
import logging
import os

# Ajustamos la ruta base para asegurar importaciones relativas limpias
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Importamos los componentes de configuración e interfaz gráfica
from config.config_manager import ConfigManager
from ui.app import App


def setup_logging() -> None:
    """
    Configura el formato y nivel del sistema de logging para depuración y diagnóstico.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main() -> None:
    """
    Función de arranque principal.
    Crea las instancias del gestor de configuración y la ventana CustomTkinter.
    """
    # Iniciamos el sistema de logs
    setup_logging()
    logger = logging.getLogger("VRShinecon.Main")
    logger.info("Iniciando VR Shinecon Media Converter...")

    try:
        # Cargamos o generamos la configuración persistente
        config_mgr = ConfigManager()

        # Instanciamos la ventana principal de la aplicación
        app = App(config_mgr=config_mgr)

        # Iniciamos el bucle de eventos de la interfaz gráfica
        app.mainloop()

        logger.info("Aplicación cerrada de forma controlada.")

    except Exception as fatal_error:
        logger.critical("Error fatal al iniciar o ejecutar la aplicación: %s", fatal_error, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
