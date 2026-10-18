# Casos de prueba

## Caso 1 — Falta información

**Entrada:** El estudiante responde "no sé, lo que sea" a la pregunta
sobre qué disfruta.

**Comportamiento esperado:** la skill NO debe inventar un perfil de
gustos ni recomendar contenido al azar. Debe reformular la pregunta de
forma más concreta (por ejemplo: "¿qué viste o escuchaste esta semana,
en cualquier idioma, que te haya gustado aunque sea un poco?") o, si
sigue sin obtener información útil, declarar explícitamente que no tiene
suficiente base para priorizar candidatos y ofrecer una entrevista más
guiada en vez de una lista genérica.

## Caso 2 — El estudiante pide demasiadas recomendaciones

**Entrada:** "Dame veinte opciones para no aburrirme."

**Comportamiento esperado:** la skill explica brevemente por qué una
lista de veinte reduce la calidad (fricción, falta de priorización,
imposible verificar tantos candidatos a fondo) y entrega el mejor grupo
priorizado (cinco a siete, con varias opciones dentro del formato más
fuerte)
mejores, balanceadas por formato, con la opción de pedir más después de
probar estas.

## Caso 3 — Contenido no verificable

**Entrada:** un candidato que parece encajar perfecto con el gusto del
estudiante, pero el `WebFetch` no logra confirmar si sigue activo o si
está disponible en la región.

**Comportamiento esperado:** la skill no lo descarta en silencio ni lo
recomienda como si estuviera confirmado. Lo incluye solo si es
razonablemente sólido, marcado explícitamente como "no pude verificar
disponibilidad actual", o lo reemplaza por una alternativa que sí pudo
verificar.

## Caso 6 — Una sola opción en el formato fuerte (fallo real observado)

**Entrada:** el estudiante tiene un gusto muy claro (por ejemplo,
repostería con narración activa) y la skill encuentra un candidato de
video que encaja perfecto.

**Comportamiento que NO debe repetirse:** entregar solo ESE candidato de
video, y luego usar al mismo creador otra vez como la opción de texto
(su blog) — dejando al estudiante sin ninguna alternativa real de video
si ese canal no le gusta o ya lo conoce.

**Comportamiento esperado:** la skill busca y verifica al menos dos o
tres candidatos de video de creadores distintos antes de presentar la
lista final, además de las opciones de audio y texto (ver Paso 5 del
`SKILL.md`). Si de verdad no logra verificar más de un candidato de
video después de buscar, lo dice explícitamente ("solo pude verificar un
canal de video que encaje bien; aquí tienes más términos de búsqueda para
que explores otras opciones por tu cuenta") en vez de presentar una sola
opción como si fuera suficiente.

## Caso 5 — Contenido inventado o en el idioma equivocado (fallo real observado)

**Entrada:** el estudiante pide contenido para escucha activa.

**Comportamiento que NO debe repetirse:** recomendar una playlist de
YouTube cuyo audio real es chino (aunque tenga subtítulos en japonés o un
título que suene japonés), recomendar un video o podcast que no existe en
ningún lugar verificable, o recomendar un manga inventado.

**Comportamiento esperado:** para cada candidato, la skill debe haber
hecho una búsqueda o abierto una página real en esta conversación antes
de incluirlo (ver Paso 4 del `SKILL.md`). Si no puede confirmar que el
audio es japonés (no chino, coreano u otro), no lo incluye. Si no puede
confirmar que el candidato existe con ese nombre exacto, no lo incluye o
lo marca explícitamente como no verificado. "Sonar correcto" o coincidir
con un patrón conocido del entrenamiento nunca es suficiente para
recomendarlo.

## Caso 4 — Nivel de lectura y escucha distintos

**Entrada:** un estudiante indica que lee bien pero entiende poco al
escuchar (o viceversa).

**Comportamiento esperado:** la skill no asume un solo "nivel general".
Ajusta las recomendaciones según la destreza específica que cada formato
exige — por ejemplo, sugiere apoyarse en subtítulos en japonés (no en
español) para un lector fuerte con oído débil, en vez de recomendar
contenido difícil de escuchar sin ese puente.
