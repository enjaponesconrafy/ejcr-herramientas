# Guía: audio condensado

Quita los silencios largos y deja solo los tramos donde se habla, para escuchar más japonés en menos tiempo. Usa los tiempos del `.ja.corregido.srt` (o `.ja.srt`) del video.

1. Necesita los subtítulos en japonés junto al video. Si faltan, sigue primero `subtitulos.md` (la traducción al español no es necesaria para este paso).
2. Ejecuta: `python scripts/crear_audio_condensado.py "videos/nombre.mp4"`
3. Crea `nombre.condensado.mp3` junto al video e imprime la duración original y la condensada.
4. Opciones:
   - `--pausa 0.8`: corta pausas de más de 0.8 s (por defecto 1.0). Más bajo = más recorte.
   - `--margen 0.3`: aire antes y después de cada tramo (por defecto 0.25).
5. Dile al estudiante que no esperes un recorte grande en narraciones continuas; en videos con música o pausas largas ahorra mucho más. Pídele que lo escuche y ajusta `--pausa` o `--margen` si se siente cortado o si quedan huecos.
