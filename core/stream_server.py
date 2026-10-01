# ==============================================================================
# PROYECTO: VR Shinecon Media Converter
# ARCHIVO: core/stream_server.py
# DESCRIPCIÓN: Servidor web local de streaming MJPEG/HTTP de latencia ultra baja.
#              Permite transmitir la pantalla SBS directamente al navegador de un
#              teléfono móvil sin necesidad de instalar aplicaciones o clientes extras.
# ==============================================================================

import io
import time
import socket
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Tuple, Any
from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger("VRShinecon.StreamServer")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Servidor HTTP multihilo capaz de transmitir concurrentemente el flujo MJPEG
    y servir peticiones HTML a múltiples clientes sin bloquearse.
    """
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        """
        Ignora silenciosamente desconexiones abruptas comunes en navegadores móviles
        (WinError 10053, ConnectionResetError, BrokenPipeError).
        """
        pass


class FrameBuffer:
    """
    Búfer de cuadros en memoria multihilo de latencia ultrabaja para streaming MJPEG.
    Permite codificación acelerada por hardware (OpenCV SIMD) y sincronización no bloqueante
    mediante threading.Condition para evitar retrasos y congelamientos.
    """

    def __init__(self) -> None:
        self.frame_bytes: bytes = b""
        self.frame_id: int = 0
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def update(self, img: Any, quality: int = 80) -> None:
        """
        Comprime la imagen SBS a formato JPEG con alta velocidad y actualiza el búfer global.
        
        Args:
            img: Imagen SBS (PIL.Image.Image, np.ndarray o bytes JPEG ya codificados).
            quality (int): Calidad de compresión JPEG (60 a 90).
        """
        try:
            if isinstance(img, (bytes, bytearray)):
                data = bytes(img)
            elif HAS_CV2 and isinstance(img, np.ndarray):
                # Codificación directa acelerada por OpenCV SIMD
                _, enc = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                data = enc.tobytes()
            elif HAS_CV2 and hasattr(img, "mode") and img.mode == "RGB":
                # Conversión de PIL RGB a OpenCV BGR y codificación nativa ultrarrápida
                arr = np.asarray(img)
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                _, enc = cv2.imencode('.jpg', bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                data = enc.tobytes()
            else:
                # Respaldo seguro en Pillow
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=False)
                data = buf.getvalue()

            with self.condition:
                self.frame_bytes = data
                self.frame_id += 1
                self.condition.notify_all()
        except Exception as error:
            logger.warning("Error comprimiendo fotograma para streaming: %s", error)

    def get_frame(self, last_id: int = -1, timeout: float = 0.5) -> Tuple[bytes, int]:
        """
        Espera hasta que haya un fotograma más reciente que last_id o venza el timeout.
        
        Returns:
            Tuple[bytes, int]: (datos JPEG del fotograma, id de fotograma).
        """
        with self.condition:
            if self.frame_id == last_id or not self.frame_bytes:
                self.condition.wait(timeout)
            return self.frame_bytes, self.frame_id


class StreamingHTTPHandler(BaseHTTPRequestHandler):
    """
    Manejador de solicitudes HTTP para servir la página web del visor y el flujo MJPEG.
    """

    # Referencia de clase al búfer compartido
    frame_buffer: Optional[FrameBuffer] = None

    def log_message(self, format: str, *args) -> None:
        """
        Sobrescribe el registro por defecto para no saturar la consola de la terminal.
        """
        pass

    def do_GET(self) -> None:
        """
        Maneja peticiones GET de clientes (celulares, navegadores).
        """
        try:
            if self.path == "/" or self.path.startswith("/index"):
                # Servimos la página web HTML5 responsiva para visores VR
                self._serve_viewer_html()
            elif self.path.startswith("/stream"):
                # Servimos el flujo continuo de video MJPEG
                self._serve_mjpeg_stream()
            elif self.path.endswith("favicon.ico"):
                self.send_response(204)
                self.end_headers()
            else:
                self.send_error(404, "Página no encontrada")
        except (ConnectionError, BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_viewer_html(self) -> None:
        """
        Envía una página web moderna con soporte de pantalla completa y bloqueo de suspensión de pantalla.
        """
        html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VR Shinecon Live Stream</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #000000;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100vw;
            height: 100vh;
            user-select: none;
            touch-action: none;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #stream-img {
            max-width: 100vw;
            max-height: 100vh;
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
            image-rendering: -webkit-optimize-contrast;
            transform: translateZ(0);
            will-change: transform;
        }
        #fullscreen-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(30, 41, 59, 0.85);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 12px 20px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            transition: opacity 0.4s ease, transform 0.2s ease;
            z-index: 999;
        }
        #fullscreen-btn:active {
            transform: scale(0.95);
        }
        .fade-out {
            opacity: 0;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <img id="stream-img" src="/stream" alt="VR Stream">
    <button id="fullscreen-btn" onclick="toggleFullscreen()">📲 Pantalla Completa VR</button>

    <script>
        let btn = document.getElementById('fullscreen-btn');
        let streamImg = document.getElementById('stream-img');
        let hideTimeout;

        // Mantener la pantalla del celular siempre encendida (Screen Wake Lock API)
        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    await navigator.wakeLock.request('screen');
                }
            } catch (err) {}
        }
        requestWakeLock();

        function resetHideTimer() {
            btn.classList.remove('fade-out');
            clearTimeout(hideTimeout);
            hideTimeout = setTimeout(() => {
                btn.classList.add('fade-out');
            }, 3000);
        }

        document.addEventListener('touchstart', resetHideTimer);
        document.addEventListener('mousemove', resetHideTimer);
        resetHideTimer();

        // Doble toque rápido para alternar pantalla completa
        let lastTap = 0;
        document.addEventListener('touchend', (e) => {
            if (e.target === btn) return;
            let now = Date.now();
            if (now - lastTap < 350 && now - lastTap > 0) {
                toggleFullscreen();
                e.preventDefault();
            }
            lastTap = now;
        });

        // Watchdog de reconexión si la red Wi-Fi sufre micro-cortes
        let lastPing = Date.now();
        setInterval(() => {
            if (Date.now() - lastPing > 4000) {
                streamImg.src = "/stream?reconnect=" + Date.now();
                lastPing = Date.now();
            }
        }, 2000);

        function toggleFullscreen() {
            let elem = document.documentElement;
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                if (elem.requestFullscreen) {
                    elem.requestFullscreen().catch(() => {});
                } else if (elem.webkitRequestFullscreen) {
                    elem.webkitRequestFullscreen();
                }
                btn.innerText = "✕ Salir de Pantalla Completa";
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen().catch(() => {});
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
                btn.innerText = "📲 Pantalla Completa VR";
            }
        }
    </script>
</body>
</html>"""
        content = html.encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionError, BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_mjpeg_stream(self) -> None:
        """
        Transmite el flujo continuo de imágenes en formato multipart/x-mixed-replace
        con latencia ultra baja, desactivando Nagle y limitando búferes para evitar lag en Wi-Fi.
        """
        try:
            # Desactivar algoritmo de Nagle (envío inmediato de paquetes)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Limitar búfer de socket a 64KB para evitar acumulación de fotogramas viejos en Wi-Fi
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        except Exception:
            pass

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Connection", "close")
        self.end_headers()

        if self.frame_buffer is None:
            return

        last_id = -1
        try:
            while True:
                frame_data, frame_id = self.frame_buffer.get_frame(last_id=last_id, timeout=0.25)
                if not frame_data or frame_id == last_id:
                    continue
                last_id = frame_id

                # Encabezado del bloque multipart
                part_header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_data)).encode("ascii") + b"\r\n\r\n"
                )
                self.wfile.write(part_header)
                self.wfile.write(frame_data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
            # El cliente cerró la pestaña o apagó el celular
            pass
        except Exception:
            pass


class LocalStreamServer:
    """
    Servidor web HTTP multihilo para retransmitir la señal VR a dispositivos móviles en la red local.
    """

    def __init__(self, port: int = 5000) -> None:
        """
        Inicializa el servidor de streaming en el puerto especificado.
        
        Args:
            port (int): Puerto de escucha TCP (por defecto 5000).
        """
        self.port = port
        self.frame_buffer = FrameBuffer()
        StreamingHTTPHandler.frame_buffer = self.frame_buffer

        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False

    def get_local_ip(self) -> str:
        """
        Determina la dirección IP de la interfaz de red local conectada al Wi-Fi o router.
        
        Returns:
            str: Dirección IP (ej. "192.168.1.15").
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Conexión ficticia hacia una IP externa para descubrir la interfaz activa
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = socket.gethostbyname(socket.gethostname())
        finally:
            s.close()
        return ip

    def get_stream_url(self) -> str:
        """
        Devuelve la dirección URL completa para abrir en el celular.
        
        Returns:
            str: URL (ej. "http://192.168.1.15:5000").
        """
        return f"http://{self.get_local_ip()}:{self.port}"

    def get_url(self) -> str:
        """
        Alias conveniente de get_stream_url().
        """
        return self.get_stream_url()

    def update_frame(self, img: Any, quality: int = 80) -> None:
        """
        Envía un nuevo fotograma compuesto al búfer de streaming.
        
        Args:
            img: Fotograma SBS listo para emitir (PIL.Image.Image, np.ndarray o bytes).
            quality (int): Nivel de calidad JPEG (60 a 90).
        """
        if self._is_running:
            self.frame_buffer.update(img, quality=quality)

    def start(self, port: Optional[int] = None) -> bool:
        """
        Inicia el servidor HTTP en un hilo daemon en segundo plano.

        Args:
            port (Optional[int]): Puerto TCP a utilizar o None para usar self.port.
        
        Returns:
            bool: True si inició correctamente.
        """
        if self._is_running:
            return True

        if port is not None:
            self.port = port

        # Buscamos un puerto disponible si el 5000 está ocupado
        target_port = self.port
        for p in range(target_port, target_port + 10):
            try:
                self._server = ThreadedHTTPServer(("0.0.0.0", p), StreamingHTTPHandler)
                self.port = p
                break
            except OSError:
                continue

        if self._server is None:
            logger.error("No se pudo enlazar ningún puerto para el servidor de streaming.")
            return False

        self._is_running = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Servidor de streaming VR iniciado en %s", self.get_stream_url())
        return True

    def stop(self) -> None:
        """
        Detiene el servidor HTTP y libera los sockets.
        """
        if not self._is_running:
            return

        self._is_running = False
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception as error:
                logger.warning("Error cerrando servidor de streaming: %s", error)
            finally:
                self._server = None

        logger.info("Servidor de streaming VR detenido.")

    def is_running(self) -> bool:
        """
        Indica si el servidor de streaming está activo actualmente.
        """
        return self._is_running
