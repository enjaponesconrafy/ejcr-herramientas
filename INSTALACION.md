# Instalación (una sola vez)

Necesitas: Python, ffmpeg, tres piezas de Python y una cuenta de Soniox. Claude Code puede instalar casi todo por ti si se lo pides desde esta carpeta; lo único que debes hacer tú es guardar tu clave de Soniox.

## 1. Claude Code
Instálalo siguiendo la guía oficial: https://docs.claude.com (busca «Claude Code» → instalación). Necesitas un plan de Claude que lo incluya. Después, abre Claude Code **dentro de esta carpeta** (`EJCR-herramientas`).

## 2. Python
- **Windows:** descarga Python desde https://www.python.org/downloads/ y, durante la instalación, marca «Add python.exe to PATH».
- **Mac:** si no lo tienes, instala desde python.org o con Homebrew (`brew install python`).
Comprueba con `python --version` (Mac: `python3 --version`).

## 3. ffmpeg
- **Windows:** `winget install Gyan.FFmpeg`
- **Mac:** `brew install ffmpeg`
Después **cierra y vuelve a abrir la terminal**. Comprueba con `ffmpeg -version`.

## 4. Piezas de Python
`python -m pip install requests janome genanki` (Mac: `python3 -m pip install ...`).

## 5. Cuenta de Soniox (transcripción)
1. Crea una cuenta en https://console.soniox.com y agrega algo de saldo (con 10 USD transcribes unas 100 horas de audio; cuesta aprox. 0.10 USD por hora).
2. Crea una clave de API (API keys).
3. Guárdala **tú mismo** como variable de entorno. **No la pegues en ningún chat.**
   - **Windows (PowerShell):** `setx SONIOX_API_KEY "tu-clave"`
   - **Mac (Terminal):** `echo 'export SONIOX_API_KEY="tu-clave"' >> ~/.zshrc`
4. Cierra y vuelve a abrir la terminal.

## ¿Qué pasa con mis videos y mi privacidad?
Para transcribir, el audio se sube a Soniox. El script lo **borra de sus servidores** apenas termina y lo confirma en pantalla («Borrado confirmado…»). Tu video original nunca se modifica. Úsalo solo para estudio personal.

## Primer uso
Copia un video a la carpeta `videos/` y dile a Claude: «Haz un mazo de Anki para el video "nombre.mp4"».
