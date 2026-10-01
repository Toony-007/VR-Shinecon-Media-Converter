# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: core/screen_capture.py
# DESCRIPCIÓN: Motor de captura de pantalla y ventanas de aplicaciones en tiempo real.
#              Permite capturar monitores completos o ventanas específicas (navegadores,
#              reproductores de video, etc.) a alta tasa de cuadros (30/60 FPS).
# ==============================================================================

import sys
import ctypes
from ctypes import wintypes
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image

# Intentamos importar mss para captura de monitores a ultra alta velocidad
try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


class ScreenCaptureEngine:
    """
    Motor encargado de capturar el contenido visual de la pantalla o de ventanas
    específicas de Windows en tiempo real para proyectarlas en formato VR SBS.
    """

    def __init__(self) -> None:
        """
        Inicializa el motor de captura y las estructuras de API de Windows.
        """
        # Instancia de MSS si está disponible
        self._sct = mss.mss() if HAS_MSS else None
        
        # Referencias a bibliotecas de Windows
        self._user32 = ctypes.windll.user32 if sys.platform == "win32" else None
        self._gdi32 = ctypes.windll.gdi32 if sys.platform == "win32" else None

    def get_monitors(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de monitores físicos o virtuales detectados en el sistema.
        
        Returns:
            List[Dict[str, Any]]: Lista de diccionarios con información de cada pantalla.
        """
        monitors_info = []

        if HAS_MSS and self._sct:
            try:
                # self._sct.monitors[0] es la combinación de todas las pantallas
                # los índices 1, 2, ... son las pantallas individuales
                for idx, m in enumerate(self._sct.monitors):
                    if idx == 0:
                        monitors_info.append({
                            "index": 0,
                            "name": f"Todas las Pantallas Combinadas ({m['width']}x{m['height']})",
                            "rect": m
                        })
                    else:
                        monitors_info.append({
                            "index": idx,
                            "name": f"Monitor {idx} ({m['width']}x{m['height']})",
                            "rect": m
                        })
                return monitors_info
            except Exception:
                pass

        # Si no está disponible MSS, devolvemos al menos la pantalla principal
        monitors_info.append({
            "index": 1,
            "name": "Monitor Principal",
            "rect": {"left": 0, "top": 0, "width": 1920, "height": 1080}
        })
        return monitors_info

    def get_open_windows(self) -> List[Tuple[int, str]]:
        """
        Enumera las ventanas visibles y con título de aplicaciones en ejecución
        (por ejemplo: Google Chrome, VLC, YouTube, navegadores web, etc.).
        
        Returns:
            List[Tuple[int, str]]: Lista de tuplas (HWND_identificador, titulo_ventana).
        """
        if not self._user32:
            return []

        windows_list: List[Tuple[int, str]] = []

        # Títulos de ventanas del sistema a omitir
        ignored_titles = {
            "", "Program Manager", "Settings", "Configuración",
            "Windows Input Experience", "Cortana", "NVIDIA GeForce Overlay"
        }

        def enum_windows_callback(hwnd: int, lparam: int) -> bool:
            # Comprobamos si la ventana es visible actualmente
            if self._user32.IsWindowVisible(hwnd):
                length = self._user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    self._user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()

                    # Filtramos ventanas vacías, invisibles o del sistema
                    if title and title not in ignored_titles and not title.startswith("MSCTFIME UI"):
                        # Verificamos que tenga dimensiones válidas
                        rect = wintypes.RECT()
                        self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 100 and h > 100:
                            windows_list.append((hwnd, title))
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        self._user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)

        return windows_list

    def capture_monitor(self, monitor_index: int = 1) -> Optional[Image.Image]:
        """
        Captura un fotograma completo del monitor seleccionado a máxima velocidad.
        
        Args:
            monitor_index (int): Índice de pantalla (1 = principal, 2 = secundario, etc.).
            
        Returns:
            Optional[Image.Image]: Fotograma capturado en formato PIL RGB.
        """
        if HAS_MSS and self._sct:
            try:
                monitors = self._sct.monitors
                if 0 <= monitor_index < len(monitors):
                    target_m = monitors[monitor_index]
                else:
                    target_m = monitors[1] if len(monitors) > 1 else monitors[0]

                sct_img = self._sct.grab(target_m)
                # Convertimos de BGRX en memoria a PIL Image RGB
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                return img
            except Exception:
                pass

        # Respaldo mediante API Win32 BitBlt
        return self._capture_desktop_dc()

    def capture_window(self, hwnd: int) -> Optional[Image.Image]:
        """
        Captura el contenido de una ventana específica por su identificador HWND.
        Utiliza PrintWindow y BitBlt para capturar incluso con composición DWM.
        
        Args:
            hwnd (int): Identificador HWND de la ventana en Windows.
            
        Returns:
            Optional[Image.Image]: Imagen de la ventana en formato RGB.
        """
        if not self._user32 or not self._gdi32:
            return None

        # Comprobamos que el HWND sea válido
        if not self._user32.IsWindow(hwnd):
            return None

        # Obtenemos las coordenadas rectangulares de la ventana
        rect = wintypes.RECT()
        self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            return None

        try:
            # Obtenemos el contexto de dispositivo de la ventana (DC)
            hwnd_dc = self._user32.GetWindowDC(hwnd)
            mfc_dc = self._gdi32.CreateCompatibleDC(hwnd_dc)
            save_bitmap = self._gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            self._gdi32.SelectObject(mfc_dc, save_bitmap)

            # Usamos PrintWindow con la bandera PW_RENDERFULLCONTENT (valor 2) para capturar aceleración GPU
            PW_RENDERFULLCONTENT = 2
            printed = self._user32.PrintWindow(hwnd, mfc_dc, PW_RENDERFULLCONTENT)

            # Si falla PrintWindow, intentamos BitBlt tradicional
            if not printed:
                SRCCOPY = 0x00CC0020
                self._gdi32.BitBlt(mfc_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)

            # Estructura BITMAPINFO para extraer los bytes de la imagen
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # Altura negativa para obtener orientación superior-a-inferior
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0   # BI_RGB

            buffer_size = width * height * 4
            buffer = ctypes.create_string_buffer(buffer_size)

            # Extraemos los bits en el búfer
            DIB_RGB_COLORS = 0
            self._gdi32.GetDIBits(mfc_dc, save_bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)

            # Liberamos los objetos GDI para prevenir fugas de memoria
            self._gdi32.DeleteObject(save_bitmap)
            self._gdi32.DeleteDC(mfc_dc)
            self._user32.ReleaseDC(hwnd, hwnd_dc)

            # Convertimos los bytes BGRA a PIL Image
            img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
            return img.convert("RGB")

        except Exception as err:
            return None

    def _capture_desktop_dc(self) -> Optional[Image.Image]:
        """
        Método de respaldo para capturar el escritorio completo mediante GDI nativo de Windows.
        """
        if not self._user32 or not self._gdi32:
            return None

        try:
            SM_CXSCREEN = 0
            SM_CYSCREEN = 1
            width = self._user32.GetSystemMetrics(SM_CXSCREEN)
            height = self._user32.GetSystemMetrics(SM_CYSCREEN)

            hdesktop = self._user32.GetDesktopWindow()
            desktop_dc = self._user32.GetWindowDC(hdesktop)
            mem_dc = self._gdi32.CreateCompatibleDC(desktop_dc)
            hbitmap = self._gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
            self._gdi32.SelectObject(mem_dc, hbitmap)

            SRCCOPY = 0x00CC0020
            self._gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, 0, 0, SRCCOPY)

            # Buffer
            buffer_size = width * height * 4
            buffer = ctypes.create_string_buffer(buffer_size)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            self._gdi32.GetDIBits(mem_dc, hbitmap, 0, height, buffer, ctypes.byref(bmi), 0)

            self._gdi32.DeleteObject(hbitmap)
            self._gdi32.DeleteDC(mem_dc)
            self._user32.ReleaseDC(hdesktop, desktop_dc)

            img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
            return img.convert("RGB")
        except Exception:
            return None
