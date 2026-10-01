# VR Shinecon Media Converter 👓

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Engine](https://img.shields.io/badge/Engine-FFmpeg-green.svg?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Streaming](https://img.shields.io/badge/Live%20Streaming-MJPEG%20%2F%20HTTP-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg?logo=windows&logoColor=white)]()

**Convierte videos e imágenes 2D a formato estereoscópico Side-by-Side (SBS) con calibración óptica y transmite tu escritorio en tiempo real vía Wi-Fi directamente a tu visor VR Shinecon o Google Cardboard.**

[Características](#-características-principales) •
[Instalación](#️-instalación-y-requisitos) •
[Guía de Uso](#-uso-de-la-aplicación) •
[Streaming en Vivo](#-streaming-y-proyección-vr-en-tiempo-real) •
[Estructura](#-estructura-modular-del-proyecto) •
[Contribución](#-contribución)

</div>

---

## 🌟 ¿Qué es VR Shinecon Media Converter?

Las gafas de realidad virtual pasivas para teléfonos inteligentes (como **VR Shinecon**, **Google Cardboard**, **BOBOVR**, etc.) utilizan lentes biconvexas circulares para enfocar cada ojo en una mitad de la pantalla del móvil. 

Sin embargo, reproducir contenido multimedia convencional 2D en estas gafas suele presentar dos grandes problemas:
1. **Estiramiento anamórfico severo**: La imagen se achata o deforma excesivamente.
2. **Distorsión en los bordes**: La curvatura de lentes económicas genera aberraciones cromáticas en las esquinas.

**VR Shinecon Media Converter** soluciona estos problemas aplicando **máscaras ópticas de lente**, corrección de relación de aspecto (1:1, 4:3, 16:9), bordes redondeados tipo visor VR180, efecto de **profundidad 3D Parallax** artificial y un **servidor web local de streaming inalámbrico** para transmitir la pantalla de tu PC al celular a ultra baja latencia.

---

## 🚀 Características Principales

### 1. Conversión Estereoscópica Side-by-Side (SBS)
- **Half SBS (HSBS)**: Divide la pantalla en dos mitades optimizadas a 1080p Full HD (estándar universal para visores móviles).
- **Full SBS (FSBS)**: Genera salida en doble resolución horizontal (3840x1080) para máxima nitidez en pantallas de alta densidad (2K/4K/OLED).
- **Soporte Multimedia Dual**: Procesa tanto archivos de **video** (`.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.webm`) como **imágenes estáticas** (`.jpg`, `.png`, `.webp`, `.bmp`).

### 2. Plantillas de Formato Óptico y Bordes Redondeados (Antideformación)
- **Eliminación del Estiramiento Horizontal**: Ajusta el contenido a formatos **Cuadrados (1:1)**, **4:3 Óptico**, **16:9 Cinema** o **Original**, encajando naturalmente en la pupila del visor.
- **Máscara de Lente VR y Curvatura Graduable**:
  - Radio de curvatura de esquina ajustable (0% a 100%) para simular máscaras de barril oculares idénticas a visores VR profesionales (VR180).
  - Separación central (IPD) y márgenes negros perimetrales para evitar distorsión cromática periférica.
- **Plantillas Predefinidas de 1 Clic**:
  1. *VR Shinecon Óptico (Cuadrado 1:1)*: Elimina el estiramiento y centra la visión.
  2. *Máscara de Visor VR180 / Barril Ocular*: Curvatura profunda envolvente.
  3. *Cine Virtual VR (16:9 Flotante)*: Pantalla panorámica en entorno oscuro.
  4. *Formato Óptico 4:3*: Relación equilibrada para móviles grandes (6.0" a 6.8").
  5. *Half SBS Estándar*: Anamórfico tradicional a pantalla completa.
  6. *Personalizado*: Control milimétrico de todos los deslizadores.

### 3. Visor de Vista Previa en Vivo (Live SBS Preview)
- Renderizado ultra rápido en memoria (3 ms) que responde instantáneamente al mover cualquier control.
- Botón **"⛶ Ampliar Vista Previa"** que despliega una ventana modal en alta definición para inspeccionar ambos ojos con aumento.

### 4. Simulación de Profundidad 3D (Parallax / Disparidad Binocular)
- Aplica un desplazamiento horizontal controlado (0 a 30 px) entre los ojos izquierdo y derecho, induciendo convergencia estereoscópica realista.

### 5. Presets y Calidad de Codificación
- **Modo Automático**: Configuración óptima de 1 clic para VR Shinecon: Formato 1:1 centrado con esquinas redondeadas a 1080p, codificación H.264, calidad preservada CRF 18 y copia de audio sin pérdida.
- **Modo Personalizado**: Control total de resolución de salida (Original, 720p, 1080p, 1440p, 4K), contenedor (MP4, MKV), aceleración por hardware (CPU libx264, NVIDIA NVENC, Intel QSV, AMD AMF), factor CRF (14 a 28) y pistas de audio.

### 6. 📡 Streaming y Proyección en Tiempo Real (Live VR Projection)
- **Captura de Pantalla Ultra Rápida**: Captura monitores completos o ventanas de aplicaciones específicas (navegadores web, YouTube, reproductores multimedia, emuladores) a 30/60 FPS usando MSS o GDI32 nativo.
- **Servidor Web MJPEG Inalámbrico**: Transmite la salida SBS por la red Wi-Fi local. ¡Abre la URL proporcionada en el navegador de tu celular (Chrome, Safari, Firefox) y colócalo en el visor sin instalar apps extrañas!
- **Modo Proyección Pantalla Completa**: Ventana inmersiva sin bordes en monitores secundarios o gafas con entrada HDMI/Type-C (salida rápida con tecla `Esc`).

### 7. Interfaz Gráfica Moderna y Fluida
- Diseñada con **CustomTkinter**, soporte nativo de **Modo Oscuro** (por defecto) y Modo Claro.
- Sistema de diseño responsivo basado en Grid con pesos dinámicos.
- Soporte **Multilingüe en tiempo real** (Español e Inglés) sin reiniciar la aplicación.
- Barra de progreso fluida y consola de registros (Log) en vivo.

---

## 📂 Estructura Modular del Proyecto

```
VR-Shinecon-Media-Converter/
│
├── main.py                     # Punto de entrada principal (Entry Point)
├── requirements.txt            # Dependencias oficiales del proyecto
├── config.example.json         # Plantilla base de configuración
├── README.md                   # Documentación y guía de usuario
├── CONTRIBUTING.md             # Guía de contribución comunitaria
├── LICENSE                     # Licencia MIT de código abierto
│
├── config/
│   ├── __init__.py
│   └── config_manager.py       # Gestor de persistencia en JSON y rutas por defecto
│
├── core/
│   ├── __init__.py
│   ├── localization.py         # Diccionario y gestor de traducciones (Español / Inglés)
│   ├── lens_mask.py            # Generador óptico de máscaras, plantillas, esquinas y bordes
│   ├── media_processor.py      # Motor de conversión FFmpeg, filtros SBS y progreso
│   ├── screen_capture.py       # Motor de captura de monitores y ventanas en tiempo real
│   └── stream_server.py        # Servidor local MJPEG/HTTP para transmisión Wi-Fi al celular
│
└── ui/
    ├── __init__.py
    ├── app.py                  # Ventana principal CustomTkinter y sistema de pestañas
    ├── tab_conversion.py       # Pestaña de conversión: cola, opciones y consola
    ├── tab_streaming.py        # Pestaña de streaming en vivo y servidor inalámbrico
    ├── tab_settings.py         # Pestaña de configuración: carpetas, temas e idioma
    ├── tab_info.py             # Guía interactiva sobre tecnología SBS y visores VR
    ├── streaming_window.py     # Ventana de proyección inmersiva a pantalla completa
    └── dialogs.py              # Ventanas modales estilizadas (Alertas, Éxito, Preview)
```

---

## ⚙️ Instalación y Requisitos

### Requisitos Previos
1. **Python 3.10 o superior** ([Descargar Python](https://www.python.org/downloads/)).
2. **FFmpeg y FFprobe** instalados y accesibles en las variables de entorno (`PATH`).
   - Puedes verificar su disponibilidad ejecutando en tu terminal:
     ```bash
     ffmpeg -version
     ```
   - *En Windows con Chocolatey / Winget*:
     ```bash
     winget install "FFmpeg (Essentials Build)"
     ```

### Clonar el Repositorio e Instalar Dependencias
```bash
git clone https://github.com/Toony-007/VR-Shinecon-Media-Converter.git
cd VR-Shinecon-Media-Converter

# (Opcional pero recomendado) Crear entorno virtual
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🖥️ Uso de la Aplicación

Inicia la aplicación ejecutando:
```bash
python main.py
```

### 1. Pestaña Conversión (Archivos Guardados)
1. Haz clic en **"📂 Importar Archivo(s)"** para seleccionar videos o imágenes.
2. Selecciona **Modo Automático** (recomendado para VR Shinecon) o activa **Modo Personalizado** para ajustar resolución, códec, aceleración por hardware o Parallax 3D.
3. Presiona **"▶ Iniciar Conversión"**. La barra de progreso y el registro te mostrarán el estado en tiempo real.

### 2. Pestaña Streaming en Vivo (Transmisión a Móvil)
1. Ve a la pestaña **"Streaming"**.
2. Selecciona la **Fuente de Captura**: puedes elegir tu monitor principal/secundario o una ventana abierta de cualquier aplicación (ej. Chrome reproduciendo una película).
3. Selecciona la plantilla óptica deseada (por ejemplo, *VR Shinecon Óptico 1:1*).
4. Elige tu modo de visualización:
   - **📡 Iniciar Servidor Streaming**: Inicia un servidor web local. La app te mostrará una dirección IP (ej. `http://192.168.1.15:8080`). Abre esa dirección en el navegador web de tu teléfono conectado a la misma red Wi-Fi y colócalo en las gafas.
   - **🖥️ Proyectar Pantalla Completa**: Abre una proyección directa a pantalla completa (ideal si tienes un segundo monitor o gafas conectadas por cable). Presiona `Esc` en cualquier momento para salir.

### 3. Pestaña Configuración
- Define la carpeta donde se guardarán tus archivos exportados.
- Selecciona el nivel de calidad predeterminado (CRF), el idioma (Español / Inglés) y el tema visual (Oscuro / Claro / Sistema).

---

## 👓 Consejos para Reproducción en VR Shinecon

1. **Alineación**: Al insertar el celular en el visor, asegúrate de que la línea negra divisoria central coincida exactamente con la división plástica del visor.
2. **Calibración IPD**: Utiliza las ruedas superiores de ajuste interpupilar de las gafas VR Shinecon hasta que la imagen no presente fatiga visual o visión doble.
3. **Reproductores Recomendados**: Si reproduces archivos guardados en tu móvil, puedes usar apps como **VLC for Android** (en modo SBS), **GizmoVR**, o **VR Player**. Para streaming en vivo, basta con el navegador web **Google Chrome** en pantalla completa.

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Si deseas colaborar con nuevas características, optimizaciones de códecs o plantillas para otros modelos de visores, consulta la [Guía de Contribución](CONTRIBUTING.md).

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.
