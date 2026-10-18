# Guía: subtítulos en japonés con traducción al español

Resultado: `nombre.ja.corregido.srt` (japonés revisado) y `nombre.es.srt` (español), con **el mismo número de subtítulos y los mismos tiempos**.

## 1. Confirmar y transcribir
1. Averigua la duración del video y dile al estudiante el costo aproximado (≈ 0.10 USD por hora). Pide confirmación.
2. Ejecuta: `python scripts/transcribir.py "videos/nombre.mp4"`
   - Genera `nombre.soniox.json`, `nombre.ja.srt` (borrador) y `nombre.dudas.txt`.
   - Sube el audio a Soniox, descarga el texto y **borra el archivo y la transcripción de sus servidores**. Al final imprime «Borrado confirmado…».
   - Si el estudiante ya transcribió ese video y solo quiere regenerar los archivos, usa `--reusar`: no vuelve a cobrar.
3. Si el script falla: lee el mensaje, explícaselo y corrige (clave sin definir, terminal sin reabrir, falta de saldo en Soniox, etc.).

## 2. Revisión de dudas (pausa obligatoria)
`nombre.dudas.txt` marca con 【 】 las partes donde Soniox tiene poca confianza, primero las urgentes (<50 %). Eso **no significa que estén mal**: muchas están bien.
- Lee **todo** el `.ja.srt`, no solo las dudas. Soniox puede equivocarse con seguridad y esos errores no aparecen marcados. Busca: palabras que no encajan con el contexto, nombres propios, anuncios o tramos en otro idioma, risas o ruidos transcritos como palabras, dos voces en un mismo subtítulo.
- Presenta al estudiante una lista corta: número de subtítulo, lo que dice, lo que sospechas y por qué. Etiquétalo como **hipótesis**.
- Pídele que escuche esos puntos (y revise el texto incrustado en el video, si lo hay) y espere su respuesta. **No continúes sin ella.**
- Si el estudiante escucha algo distinto, manda su oído.

## 3. Crear el japonés corregido
- Copia `nombre.ja.srt` a `nombre.ja.corregido.srt` y aplica las correcciones del estudiante. **No cambies los tiempos.**
- Si hay un tramo que no es japonés (anuncio en inglés, música con letra), sustituye su texto por `……`. Mantén el subtítulo, para que las traducciones sigan alineadas. Los scripts descartan las tarjetas sin japonés.
- Si el estudiante borra subtítulos, la numeración puede saltar; no importa: los scripts leen por orden.

## 4. Traducir al español
- Un subtítulo japonés → una línea en español, en el mismo orden. Total idéntico.
- Español latinoamericano neutro, tuteo, natural y fiel al registro (hablado, formal, narrativo).
- Cada línea debe leerse bien sola y también encajar al unirla con las vecinas: el japonés a veces corta a mitad de oración.
- Conserva nombres propios (mantén el seudónimo si el hablante dice que es falso) y explica en una nota breve entre paréntesis solo lo imprescindible (un juego de palabras o doble sentido que no se puede traducir).
- Si el estudiante es principiante, no simplifiques el español de más: queremos que lo entienda, no que lo memorice mal.
- Guarda `nombre.es.srt` con los mismos números de subtítulo y tiempos que el japonés. Verifica que la cantidad sea igual antes de seguir: `crear_anki.py` se detiene si no coincide.

## 5. Entregar
Dile al estudiante dónde quedaron los archivos y pregúntale si quiere pasar a las tarjetas de Anki (`anki.md`) o al audio condensado (`audio-condensado.md`).
