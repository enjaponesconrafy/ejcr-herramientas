# Guía: mazo de Anki con captura y audio

Requiere `nombre.ja.corregido.srt` (o `.ja.srt`) y `nombre.es.srt` junto al video, con el mismo número de subtítulos. Si faltan, sigue primero `subtitulos.md`.

Cada tarjeta: **frente** = captura de pantalla + audio de la frase; **reverso** = japonés, español y contexto (frases vecinas, oculto).

## 1. Elegir el modo
- **Por defecto** (junta subtítulos en frases completas, máximo 6 s y 40 caracteres): úsalo cuando el audio es rápido o los subtítulos son fragmentos.
  `python scripts/crear_anki.py "videos/nombre.mp4"`
- **`--por-subtitulo`**: una tarjeta por subtítulo, respetando los cortes del .srt. Úsalo cuando el estudiante ya revisó los cortes y quiere tarjetas cortas, o si las tarjetas del modo por defecto le salen demasiado largas.
  `python scripts/crear_anki.py "videos/nombre.mp4" --por-subtitulo`
- Ajustes: `--max 5` (segundos máximos), `--max-caracteres 30`, `--mazo "Nombre del mazo"`, `--resumen "de qué trata"` (se muestra oculto en cada tarjeta).

## 2. Subtítulos incrustados en el video
Pregunta si el video trae subtítulos quemados en la imagen. Si sí, aparecerían en el frente de la tarjeta y revelarían el audio.
- Saca una captura de prueba (`ffmpeg -ss 30 -i "videos/nombre.mp4" -frames:v 1 prueba.jpg`), mira cuánto ocupa la banda y recorta con `--recorte-abajo 20` (porcentaje; ajusta según la banda) o `--recorte-arriba N`.
- Si no hay subtítulos incrustados, **no uses recorte**.

## 3. Revisar y entregar
- El script crea `nombre.apkg` junto al video. Imprime cuántas tarjetas hizo.
- Pide al estudiante que revise un par de tarjetas: que la captura no muestre el texto, que el audio entre completo, que el largo le sirva.
- Para importar: doble clic en el `.apkg`, o en Anki: Archivo → Importar.
- **Si va a regenerar un mazo que ya importó, debe borrar primero el anterior en Anki**; si no, se mezclan.
- Si el contador se queda quieto: en Windows, presionar Enter en la ventana; el script detiene ffmpeg si una tarjeta tarda más de 3 minutos.
