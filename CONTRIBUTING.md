# Guía de Contribución 🤝

¡Gracias por tu interés en contribuir a **VR Shinecon Media Converter**!

Este proyecto es de código abierto y agradecemos cualquier tipo de contribución: corrección de errores, mejoras de rendimiento, optimizaciones en los filtros de FFmpeg, nuevas plantillas ópticas o soporte para más visores y lentes VR.

---

## 🛠️ ¿Cómo empezar?

1. **Haz un Fork** del repositorio en GitHub:
   ```bash
   https://github.com/Toony-007/VR-Shinecon-Media-Converter
   ```

2. **Clona tu fork** localmente:
   ```bash
   git clone https://github.com/TU-USUARIO/VR-Shinecon-Media-Converter.git
   cd VR-Shinecon-Media-Converter
   ```

3. **Crea un entorno virtual** e instala las dependencias:
   ```bash
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   # En Linux / macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

4. **Verifica FFmpeg**:
   Asegúrate de tener `ffmpeg` y `ffprobe` en el `PATH` del sistema.

5. **Ejecuta la aplicación**:
   ```bash
   python main.py
   ```

---

## 🌿 Flujo de Trabajo Git

1. Crea una rama para tu característica o corrección:
   ```bash
   git checkout -b feature/nombre-de-tu-mejora
   # o
   git checkout -b fix/descripcion-del-bug
   ```

2. Realiza tus cambios manteniendo el estilo del código:
   - Usa nombres descriptivos en español o inglés técnico coherente.
   - Incluye comentarios explicativos (Docstrings PEP 257 y anotaciones de tipo PEP 484).
   - Mantén desacoplada la interfaz (`ui/`) de la lógica del núcleo (`core/`).

3. Haz commits claros y atómicos siguiendo Conventional Commits:
   ```bash
   git commit -m "feat: agregar soporte para preset de visor BoboVR Z6"
   git commit -m "fix: solucionar fuga de memoria en captura de pantalla MJPEG"
   ```

4. Sube tu rama a tu fork:
   ```bash
   git push origin feature/nombre-de-tu-mejora
   ```

5. Abre un **Pull Request** hacia la rama `main` del repositorio oficial.

---

## 🐛 Reportar Errores

Si encuentras un bug o comportamiento inesperado:
- Abre un **Issue** en GitHub.
- Describe los pasos exactos para reproducirlo.
- Adjunta el archivo o formato multimedia con el que ocurrió (resolución, códec, etc.).
- Incluye el sistema operativo y la versión de FFmpeg (`ffmpeg -version`).
- Adjunta los mensajes relevantes de la consola de log.

---

## 💡 Sugerir Funcionalidades

¿Tienes una idea para hacer la experiencia VR aún más inmersiva?
Abre un **Issue** con la etiqueta `enhancement` o participa en las discusiones del repositorio detallando el caso de uso y cómo beneficiaría a los usuarios.
