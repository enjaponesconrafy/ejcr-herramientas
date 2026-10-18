# Guía: procesar contenido de YouTube (descargar, subtitular, Anki y audio condensado)

Esta guía es el director de orquesta. Se usa cuando el estudiante entrega un **enlace** (video, lista o canal) en vez de un archivo, o cuando pide varias cosas a la vez. Se encarga de descargar el video y luego sigue, en orden, las otras guías: `subtitulos.md`, `anki.md` y `audio-condensado.md`.

Resultado: el video en `videos/` y, según lo que pida el estudiante, `nombre.ja.corregido.srt`, `nombre.es.srt`, el mazo `.apkg` y el audio condensado, todos junto al video y con su mismo nombre.

## 1. Pregunta todo al inicio, en un solo mensaje

Antes de tocar nada, pregunta esto junto (si tienes la herramienta de preguntas con opciones, úsala):

1. **¿De dónde viene el contenido?** Un video, una lista de reproducción, un canal completo, o un archivo que ya está en `videos/`.
2. **¿Qué quiere obtener?** Puede elegir cualquier combinación:
   - Subtítulos en japonés y español
   - Mazo de Anki con audio y captura
   - Audio condensado (sin silencios largos)
3. **Si es lista o canal:** ¿todos los videos o solo algunos? (ver paso 3).

No preguntes qué servicio de transcripción usar: aquí siempre es Soniox. Solo comprueba, sin mostrar su valor, que existe la variable `SONIOX_API_KEY` (regla 3 de `CLAUDE.md`).

Espera la respuesta antes de empezar.

## 2. Comprueba que las piezas están listas

Haz estas comprobaciones una vez por sesión, además de las de `CLAUDE.md`:

- `yt-dlp --version`
- `ffmpeg -version` (yt-dlp lo necesita para unir el video con el audio)
- `deno --version`. YouTube cambia a menudo y yt-dlp necesita un entorno de JavaScript para entenderlo; Deno es el que usa por defecto.

Si falta algo, explica en una frase para qué sirve y ofrécete a instalarlo siguiendo `INSTALACION.md`. Tras instalar, el estudiante debe **cerrar y volver a abrir la terminal**.

Si `yt-dlp` tiene más de unos tres meses o una descarga falla de forma rara, **actualízalo primero**: `python -m pip install -U "yt-dlp[default]"` (en Mac, `python3 -m pip ...`). Es el arreglo más frecuente.

**Si Windows dice que `yt-dlp` no se reconoce como comando** pero `python -m yt_dlp --version` sí responde, yt-dlp está instalado y solo falta agregar su carpeta al PATH. Haz esto, explicándoselo en palabras simples:

1. Averigua la carpeta: `python -c "import sysconfig; print(sysconfig.get_path('scripts'))"` y confirma que contiene `yt-dlp.exe`. Si no está ahí, busca en la carpeta Scripts de la instalación de usuario: `python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"`.
2. Pide permiso al estudiante para cambiar su PATH de usuario (es un cambio permanente en su computadora). Si acepta, ejecuta en PowerShell, sustituyendo `CARPETA` por la ruta que encontraste: `[Environment]::SetEnvironmentVariable("Path", ([Environment]::GetEnvironmentVariable("Path","User") + ";CARPETA"), "User")`
3. Dile que **cierre y vuelva a abrir la terminal** y comprueba con `yt-dlp --version`.

Mientras eso no esté arreglado, puedes seguir usando `python -m yt_dlp` en lugar de `yt-dlp` en todos los comandos de esta guía.

## 3. Si es una lista o un canal, confirma la escala

Cuenta los videos sin descargar nada:

`yt-dlp --flat-playlist --print "%(id)s" "URL"`

Cuenta tú las líneas del resultado. No uses `wc -l`: no existe en Windows.

Calcula también, si puedes, la duración total: `yt-dlp --flat-playlist --print "%(duration)s" "URL"` (algunos videos pueden salir sin dato; dilo si pasa).

Dile al estudiante, en palabras simples:
- Cuántos videos son y cuántas horas suman, aproximadamente.
- Que cada video se descarga **y** se transcribe, y que la transcripción cuesta dinero (≈ 0.10 USD por hora de audio): horas totales × 0.10.
- Que un lote grande tarda mucho y ocupa espacio en disco (los videos pesan cientos de MB por hora).
- Que puede elegir todos o un subconjunto (por ejemplo los 5 primeros: `--playlist-items 1-5`).

**Recomendación por defecto para lotes de más de 5 videos:** empezar con 1 o 2, que el estudiante revise el resultado y luego seguir. Esta confirmación de costo sirve para todo el lote: no la repitas por cada video. La revisión de dudas del paso 7 sí es por video.

## 4. Descarga

Trabaja siempre desde la carpeta principal del repositorio y guarda en `videos/`.

La selección de formato (`-f`) pide video H.264 (`avc1`), porque es el que `ffmpeg` procesa más rápido para las capturas y los clips, y limita la imagen a 1080p (Full HD): se ve nítido al reproducirlo y evita bajar 4K, que pesa muchísimo y no aporta para estudiar. Si el estudiante tiene poco espacio o internet lento, puedes bajar el tope a 720p cambiando `1080` por `720` en el comando; dile que se verá menos nítido. Si ese formato no existe, cae a otro mp4 (que puede ser AV1, más lento de procesar) y al final a lo mejor disponible.

**Un solo video**

```
yt-dlp --no-playlist -P videos -f "bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4][height<=1080]/bv*[height<=1080]+ba/b" --merge-output-format mp4 --windows-filenames -o "%(title).100B.%(ext)s" "URL"
```

(`--no-playlist` evita bajar una lista entera cuando el enlace del video trae una lista pegada.)

**Lista o canal**

```
yt-dlp -P videos -f "bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4][height<=1080]/bv*[height<=1080]+ba/b" --merge-output-format mp4 --windows-filenames --download-archive videos/descargados.txt --sleep-interval 3 --max-sleep-interval 8 -o "%(playlist_index)03d_%(title).100B.%(ext)s" "URL"
```

Qué hace cada pieza (explícalo solo si el estudiante pregunta):
- `-P videos`: guarda en la carpeta `videos/`.
- `--windows-filenames`: quita del título los símbolos que Windows no admite.
- `--download-archive videos/descargados.txt`: apunta qué videos ya bajó; si se corta o se vuelve a ejecutar, no repite los que ya están.
- `--sleep-interval 3 --max-sleep-interval 8`: pausa breve entre descargas para no saturar el servidor.

Sustituye `URL` por el enlace, entre comillas. Tras descargar, **verifica** cada archivo: que exista, que no esté vacío y que tenga video y audio (`ffprobe`). Dile al estudiante dónde quedó y cuánto dura.

## 5. Nombres de archivo

- Los nombres con caracteres japoneses funcionan: los scripts reciben la ruta entre comillas. **No renombres por costumbre.**
- Renombra solo si un paso falla por culpa del nombre (emojis, símbolos raros, ruta demasiado larga). En ese caso crea un nombre corto y simple en minúsculas, con palabras separadas por guion bajo, y dile al estudiante cuál usaste.
- Solo puedes renombrar un archivo que tú descargaste. Un archivo que el estudiante trajo por su cuenta no se toca (regla 5 de `CLAUDE.md`).
- Si dos videos terminan con el mismo nombre, no sobrescribas: añade el número de la lista o el identificador del video al final.

## 6. Cuando la descarga falla

| Síntoma | Qué hacer |
|---|---|
| Error de formato, `403`, «no video formats» o fallos raros | Actualiza yt-dlp (paso 2) y reintenta una vez. Comprueba también que Deno está instalado. |
| «Sign in to confirm you're not a bot» | Actualiza y reintenta. Si sigue, explica la opción de las cookies (abajo) y deja que el estudiante decida. |
| Video privado, de pago, solo para miembros, con restricción de edad o bloqueado en su país | **No intentes saltártelo.** Dilo claramente y pide un archivo local o que lo descargue por su cuenta. |
| Transmisión en vivo o estreno que aún no termina | Sáltalo y avisa. |
| Un video falla dentro de una lista | Sigue con los demás, anota cuál falló y repórtalo al final. |

**Cookies del navegador (último recurso, solo si el estudiante lo acepta).** `--cookies-from-browser firefox` (o `chrome`, `edge`) hace que yt-dlp use la sesión que el estudiante ya tiene abierta. Explícale antes que eso da acceso a su cuenta de YouTube y que es mejor usar una cuenta secundaria. No leas, copies ni pegues el contenido de las cookies en el chat. Si el navegador está abierto y falla, pídele que lo cierre y reintenta.

Si nada funciona, no insistas con trucos: pide un archivo local, un archivo de subtítulos o una transcripción y sigue desde ahí.

## 7. Procesar: orden y pausas

Una vez descargado, sigue las demás guías en este orden:

1. **Transcribir** con `subtitulos.md` (paso 1). Se hace **de un video a la vez**, nunca en paralelo: Soniox tiene límite de trabajos simultáneos y subir varios a la vez puede cortar la conexión y gastar dinero en reintentos.
2. **Pausa obligatoria de revisión** (regla 2 de `CLAUDE.md`). Muestra las partes dudosas de ese video y espera las correcciones del estudiante antes de traducir o crear nada. En un lote esto va **por video**: puedes transcribir todos primero, pero no traduzcas ni crees mazos de un video hasta que el estudiante revise sus dudas.
3. **Traducir** con `subtitulos.md`, si pidió subtítulos o mazo.
4. **Mazo de Anki** con `anki.md`, si lo pidió.
5. **Audio condensado** con `audio-condensado.md`, si lo pidió.

Al terminar cada video, di en una línea qué quedó listo antes de pasar al siguiente.

## 8. Informe final

Al terminar, dile al estudiante, en pocas líneas:
- Qué archivos se generaron y en qué carpeta están.
- Cuántos videos se procesaron y cuál es el costo aproximado de transcripción.
- Qué videos fallaron o se saltaron, y por qué.
- Qué tiene pendiente de revisar, si queda algo.

Recuérdale que los videos descargados y todo lo que se generó a partir de ellos son **para estudio personal**: no se comparten ni se publican (regla 6). Si necesita espacio, ofrécete a borrar los videos descargados, pero **solo si él lo pide**; no borres nada por tu cuenta.

## Notas

- Las etiquetas de idioma de los videos de YouTube no son confiables: a veces marcan como «inglés» un audio que es japonés. Si algún paso decide por el idioma del audio, usa siempre la primera pista de audio.
- Descargar de YouTube puede ir contra sus términos de servicio. Por eso esta guía es solo para uso personal de estudio, nunca para redistribuir.
- Si un video trae subtítulos hechos por una persona, puedes mencionárselo al estudiante (`yt-dlp --list-subs "URL"`) como referencia para comparar, pero la fuente de verdad sigue siendo el audio (regla 1).
