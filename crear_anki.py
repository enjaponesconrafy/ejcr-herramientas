"""Paso 4: crea un mazo de Anki (.apkg) con una tarjeta por frase completa.

Frente de la tarjeta: captura de pantalla + audio de la frase.
Reverso: japonés, español y un contexto oculto (frases vecinas y resumen opcional).

Uso:
  python crear_anki.py "video.mp4"
  python crear_anki.py "video.mp4" --mazo "Nombre del mazo" --resumen "De qué trata el episodio"
  python crear_anki.py "video.mp4" --max 5     (tarjetas más cortas: máximo 5 segundos)
  python crear_anki.py "video.mp4" --max 4 --max-caracteres 30   (todavía más cortas)
  python crear_anki.py "video.mp4" --por-subtitulo   (una tarjeta por subtítulo: respeta tus cortes del .srt)
  python crear_anki.py "video.mp4" --recorte-abajo 20
        (si el video trae subtítulos incrustados abajo, quita ese 20 % de la captura)

Busca junto al video estos archivos (los que genera transcribir.py y la traducción):
  <video>.ja.corregido.srt  (si no existe, usa <video>.ja.srt)
  <video>.es.srt
Necesita: ffmpeg instalado y la pieza genanki (python -m pip install genanki).
Trabaja solo con copias: el video original no se modifica.
"""
import argparse
import hashlib
import itertools
import math
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import genanki
except ImportError:
    sys.exit("Falta la pieza genanki. Instálala con: python -m pip install genanki")

TIEMPO = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")
FIN_FRASE = "。？！?!"
CIERRA = "」』）)"

# Reglas de las tarjetas (valores de partida, se ajustan con clips reales)
MARGEN_S = 0.20          # se añade antes y después del audio de cada frase
MIN_DURACION_S = 1.0     # frases más cortas se descartan
MAX_DURACION_S = 6.0     # una tarjeta más larga que esto se parte en trozos
MAX_CARACTERES = 40      # idem, por cantidad de caracteres
MIN_CARACTERES = 6       # sin contar puntuación
VECINAS = 2              # frases de contexto antes y después

# Identificadores fijos del tipo de nota: no cambiar, o Anki creará un tipo nuevo
MODELO_ID = 1760654321


def a_segundos(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def leer_srt(ruta):
    texto = Path(ruta).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    cues = []
    for bloque in texto.strip().split("\n\n"):
        lineas = bloque.split("\n")
        for i, linea in enumerate(lineas):
            m = TIEMPO.search(linea)
            if m:
                g = m.groups()
                cues.append({"ini": a_segundos(*g[:4]), "fin": a_segundos(*g[4:]),
                             "texto": "".join(lineas[i + 1:]).strip()})
                break
    return cues


def agrupar_frases(ja, es, max_s=None):
    """Junta subtítulos consecutivos hasta completar una frase; parte las muy largas."""
    max_s = max_s or MAX_DURACION_S
    frases, actual = [], []

    def cerrar():
        if actual:
            frases.extend(partir(list(actual), max_s))
            actual.clear()

    for i, (c, e) in enumerate(zip(ja, es)):
        actual.append((c, e))
        fin = c["texto"].rstrip(CIERRA)
        pausa = (ja[i + 1]["ini"] - c["fin"]) if i + 1 < len(ja) else 99
        if (fin and fin[-1] in FIN_FRASE) or pausa >= 1.5:
            cerrar()
    cerrar()
    return frases


def agrupar_por_subtitulo(ja, es, min_s=1.2, min_chars=8):
    """Una tarjeta por subtítulo, respetando los cortes del .srt.
    Solo junta subtítulos muy cortos con el siguiente, para no crear tarjetas de una sílaba."""
    frases, actual = [], []
    for i, (c, e) in enumerate(zip(ja, es)):
        actual.append((c, e))
        dur = actual[-1][0]["fin"] - actual[0][0]["ini"]
        chars = largo_util("".join(x["texto"] for x, _ in actual))
        pausa = (ja[i + 1]["ini"] - c["fin"]) if i + 1 < len(ja) else 99
        if (dur >= min_s and chars >= min_chars) or pausa >= 1.5 or i == len(ja) - 1:
            frases.append(armar(actual))
            actual = []
    return frases


def armar(trozo):
    return {
        "ini": trozo[0][0]["ini"], "fin": trozo[-1][0]["fin"],
        "ja": "".join(c["texto"] for c, _ in trozo),
        "es": " ".join(e["texto"] for _, e in trozo),
    }


def partir(trozo, max_s):
    """Si la frase es muy larga, la parte en 2 o 3 tarjetas, cortando entre subtítulos."""
    dur = trozo[-1][0]["fin"] - trozo[0][0]["ini"]
    chars = sum(len(c["texto"]) for c, _ in trozo)
    n0 = max(1, math.ceil(max(dur / max_s, chars / MAX_CARACTERES)))
    if n0 == 1:
        return [armar(trozo)]

    def bonus(b):  # b = corte antes del subtítulo b
        previo, sig = trozo[b - 1][0], trozo[b][0]
        texto = previo["texto"].rstrip(CIERRA)
        puntos = 0.0
        if texto.endswith(("、", "。", "？", "！")):
            puntos += 0.8   # cortar en una coma o final de frase
        if "。" in texto[:-1] or "？" in texto[:-1]:
            puntos += 1.5   # el subtítulo ya trae un final de frase dentro
        if sig["ini"] - previo["fin"] >= 0.5:
            puntos += 0.8   # o donde hay una pausa
        return puntos

    def cabe(limites):
        for a, b in zip(limites, limites[1:]):
            d = trozo[b - 1][0]["fin"] - trozo[a][0]["ini"]
            c = sum(len(x["texto"]) for x, _ in trozo[a:b])
            if d > max_s or c > MAX_CARACTERES:
                return False
        return True

    # Se prueba con 2, 3... trozos hasta que todos quepan en el límite; si no es posible
    # (un subtítulo suelto ya es largo), se queda con la mejor división que haya.
    mejor_global = None
    for n in range(min(n0, len(trozo)), len(trozo) + 1):
        objetivo = dur / n
        mejor, mejor_costo = None, None
        for cortes in itertools.combinations(range(1, len(trozo)), n - 1):
            limites = [0, *cortes, len(trozo)]
            if not cabe(limites):
                continue
            costo = sum(((trozo[b - 1][0]["fin"] - trozo[a][0]["ini"]) - objetivo) ** 2
                        for a, b in zip(limites, limites[1:]))
            costo -= sum(bonus(b) for b in cortes)
            if mejor_costo is None or costo < mejor_costo:
                mejor, mejor_costo = limites, costo
        if mejor:
            mejor_global = mejor
            break
    if mejor_global is None:  # nada cabe: se corta en todos los subtítulos
        mejor_global = list(range(len(trozo) + 1))
    return [armar(trozo[a:b]) for a, b in zip(mejor_global, mejor_global[1:])]


def largo_util(texto):
    return len(re.sub(r"[、。，．！？?!「」『』（）()・…\s]", "", texto))


def ffmpeg(*args):
    # -nostdin: ffmpeg no se queda esperando teclas en la terminal
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *args],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=180)
    except subprocess.TimeoutExpired:
        sys.exit("\nffmpeg tardó demasiado en una tarjeta y lo detuve. "
                 "Vuelve a ejecutar el comando; si se repite, avísame.")
    if r.returncode != 0:
        sys.exit(f"ffmpeg falló:\n{r.stderr[:600]}")


def esc(t):
    return html.escape(t, quote=False)


MODELO = genanki.Model(
    MODELO_ID, "EJCR frase con audio y captura",
    fields=[{"name": "Captura"}, {"name": "Audio"}, {"name": "Japones"},
            {"name": "Espanol"}, {"name": "Contexto"}],
    templates=[{
        "name": "Escuchar y recordar",
        "qfmt": "<div style='text-align:center'>{{Captura}}<br>{{Audio}}</div>",
        "afmt": ("{{FrontSide}}<hr id=answer>"
                 "<div style='text-align:center;font-size:26px'>{{Japones}}</div>"
                 "<div style='text-align:center;font-size:20px;margin-top:10px'>{{Espanol}}</div>"
                 "<details style='margin-top:14px;color:#777;font-size:15px'>"
                 "<summary>Contexto</summary>{{Contexto}}</details>"),
    }],
    css=".card{font-family:'Yu Gothic','Meiryo',sans-serif;text-align:center}img{max-width:100%}",
)


def main():
    global MAX_CARACTERES
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--ja")
    ap.add_argument("--es")
    ap.add_argument("--mazo")
    ap.add_argument("--resumen", default="")
    ap.add_argument("--recorte-abajo", type=float, default=0,
                    help="porcentaje de la captura que se quita por abajo (subtítulos incrustados)")
    ap.add_argument("--recorte-arriba", type=float, default=0,
                    help="porcentaje de la captura que se quita por arriba")
    ap.add_argument("--por-subtitulo", action="store_true",
                    help="una tarjeta por subtítulo del .srt, sin juntar frases (respeta tus cortes)")
    ap.add_argument("--max", type=float, default=MAX_DURACION_S,
                    help="duración máxima de una tarjeta en segundos (por defecto 6)")
    ap.add_argument("--max-caracteres", type=int, default=MAX_CARACTERES,
                    help="máximo de caracteres japoneses por tarjeta (por defecto 40)")
    a = ap.parse_args()
    MAX_CARACTERES = a.max_caracteres

    video = Path(a.video)
    if not video.is_file():
        sys.exit(f"No encuentro el video: {video}")
    if not shutil.which("ffmpeg"):
        sys.exit("No encuentro ffmpeg. Instálalo con: winget install Gyan.FFmpeg "
                 "(y reabre PowerShell).")
    base = video.with_suffix("")
    ja_ruta = Path(a.ja) if a.ja else (
        Path(str(base) + ".ja.corregido.srt") if Path(str(base) + ".ja.corregido.srt").is_file()
        else Path(str(base) + ".ja.srt"))
    es_ruta = Path(a.es) if a.es else Path(str(base) + ".es.srt")
    for r in (ja_ruta, es_ruta):
        if not r.is_file():
            sys.exit(f"No encuentro el archivo de subtítulos: {r}")
    ja, es = leer_srt(ja_ruta), leer_srt(es_ruta)
    if len(ja) != len(es):
        sys.exit(f"El japonés tiene {len(ja)} subtítulos y el español {len(es)}. "
                 "Deben tener el mismo número, en el mismo orden.")

    frases = (agrupar_por_subtitulo(ja, es) if a.por_subtitulo
              else agrupar_frases(ja, es, a.max))
    elegidas = [i for i, f in enumerate(frases)
                if MIN_DURACION_S <= f["fin"] - f["ini"] <= MAX_DURACION_S
                and largo_util(f["ja"]) >= MIN_CARACTERES]

    quitar = a.recorte_abajo + a.recorte_arriba
    if not 0 <= quitar < 80:
        sys.exit("Los recortes suman demasiado: deja al menos el 20 % de la imagen.")
    filtro_imagen = "scale=640:-2"
    if quitar:
        alto = 1 - quitar / 100
        filtro_imagen = (f"crop=iw:trunc(ih*{alto:.4f}/2)*2:0:trunc(ih*{a.recorte_arriba / 100:.4f}/2)*2,"
                         "scale=640:-2")

    nombre = a.mazo or video.stem
    sello = hashlib.sha1(nombre.encode("utf-8")).hexdigest()
    mazo = genanki.Deck(int(sello[:8], 16) % (1 << 30) + (1 << 30), nombre)
    medios = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for n, i in enumerate(elegidas, 1):
            f = frases[i]
            ini = max(0.0, f["ini"] - MARGEN_S)
            dur = f["fin"] - f["ini"] + 2 * MARGEN_S
            audio = f"ejcr_{sello[:8]}_{n:03}.mp3"
            captura = f"ejcr_{sello[:8]}_{n:03}.jpg"
            ffmpeg("-ss", f"{ini:.3f}", "-t", f"{dur:.3f}", "-i", str(video),
                   "-vn", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "5", str(tmp / audio))
            medio = f["ini"] + (f["fin"] - f["ini"]) / 2
            ffmpeg("-ss", f"{medio:.3f}", "-i", str(video), "-frames:v", "1",
                   "-vf", filtro_imagen, "-q:v", "4", str(tmp / captura))
            medios += [str(tmp / audio), str(tmp / captura)]

            antes = [frases[j]["ja"] for j in range(max(0, i - VECINAS), i)]
            despues = [frases[j]["ja"] for j in range(i + 1, min(len(frases), i + 1 + VECINAS))]
            partes = []
            if a.resumen:
                partes.append(f"<p><i>{esc(a.resumen)}</i></p>")
            if antes:
                partes.append("<p>Antes: " + " ".join(esc(x) for x in antes) + "</p>")
            if despues:
                partes.append("<p>Después: " + " ".join(esc(x) for x in despues) + "</p>")

            mazo.add_note(genanki.Note(
                model=MODELO,
                fields=[f"<img src='{captura}'>", f"[sound:{audio}]", esc(f["ja"]),
                        esc(f["es"]), "".join(partes)],
                guid=genanki.guid_for(nombre, f["ja"]),
            ))
            print(f"  tarjeta {n}/{len(elegidas)}", end="\r")

        paquete = genanki.Package(mazo)
        paquete.media_files = medios
        salida = Path(str(base) + ".apkg")
        paquete.write_to_file(str(salida))

    print(f"\nListo: {len(elegidas)} tarjetas (de {len(frases)} frases) en:\n{salida}")
    print("Ábrelo con doble clic o desde Anki: Archivo > Importar.")


if __name__ == "__main__":
    main()
