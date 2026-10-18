"""Paso 5: crea un audio condensado (sin silencios largos) a partir de un video y sus subtítulos.

Conserva solo los tramos donde alguien habla (según los tiempos del .srt) y quita las pausas
largas, la música sola y los silencios. Sirve para escuchar mucho más contenido en menos tiempo.

Uso:
  python crear_audio_condensado.py "video.mp4"
  python crear_audio_condensado.py "video.mp4" --pausa 0.8     (corta pausas de más de 0.8 s)
  python crear_audio_condensado.py "video.mp4" --margen 0.3    (aire antes y después de cada tramo)

Busca junto al video <video>.ja.corregido.srt (si no existe, usa <video>.ja.srt).
Crea <video>.condensado.mp3 junto al video. El original no se modifica.
Necesita: ffmpeg instalado.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIEMPO = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def a_segundos(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def leer_tiempos(ruta):
    tramos = []
    for linea in Path(ruta).read_text(encoding="utf-8-sig").splitlines():
        m = TIEMPO.search(linea)
        if m:
            g = m.groups()
            tramos.append((a_segundos(*g[:4]), a_segundos(*g[4:])))
    return sorted(tramos)


def duracion(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(ruta)], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"ffprobe no pudo leer la duración:\n{r.stderr[:400]}")
    return float(r.stdout.strip())


def armar_tramos(subs, pausa, margen, total):
    """Une subtítulos separados por pausas cortas; añade margen; une lo que se solape."""
    unidos = []
    for ini, fin in subs:
        if unidos and ini - unidos[-1][1] <= pausa:
            unidos[-1][1] = max(unidos[-1][1], fin)
        else:
            unidos.append([ini, fin])
    tramos = []
    for ini, fin in unidos:
        ini, fin = max(0.0, ini - margen), min(total, fin + margen)
        if tramos and ini <= tramos[-1][1]:
            tramos[-1][1] = max(tramos[-1][1], fin)
        else:
            tramos.append([ini, fin])
    return tramos


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--ja")
    ap.add_argument("--pausa", type=float, default=1.0,
                    help="pausas más largas que esto (segundos) se cortan; por defecto 1.0")
    ap.add_argument("--margen", type=float, default=0.25,
                    help="aire antes y después de cada tramo (segundos); por defecto 0.25")
    a = ap.parse_args()

    video = Path(a.video)
    if not video.is_file():
        sys.exit(f"No encuentro el archivo: {video}")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit("No encuentro ffmpeg. Instálalo con: winget install Gyan.FFmpeg "
                 "(y reabre PowerShell).")
    base = video.with_suffix("")
    corregido = Path(str(base) + ".ja.corregido.srt")
    ja = Path(a.ja) if a.ja else (corregido if corregido.is_file() else Path(str(base) + ".ja.srt"))
    if not ja.is_file():
        sys.exit(f"No encuentro los subtítulos: {ja}")

    subs = leer_tiempos(ja)
    if not subs:
        sys.exit("El archivo de subtítulos no tiene tiempos.")
    total = duracion(video)
    tramos = armar_tramos(subs, a.pausa, a.margen, total)

    # El grafo va en un archivo aparte: con cientos de tramos, la línea de comandos sería demasiado larga
    partes = [f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{i}]"
              for i, (s, e) in enumerate(tramos)]
    etiquetas = "".join(f"[a{i}]" for i in range(len(tramos)))
    grafo = ";\n".join(partes) + f";\n{etiquetas}concat=n={len(tramos)}:v=0:a=1[out]"
    salida = Path(str(base) + ".condensado.mp3")
    with tempfile.TemporaryDirectory() as tmp:
        guion = Path(tmp) / "grafo.txt"
        guion.write_text(grafo, encoding="utf-8")
        # Según la versión de ffmpeg, el archivo con el grafo se pasa con una opción u otra.
        # Se prueban en orden; la última pone el grafo directo en la línea de comandos.
        variantes = [["-/filter_complex", str(guion)],
                     ["-filter_complex_script", str(guion)],
                     ["-filter_complex", grafo]]
        r = None
        for opcion in variantes:
            try:
                r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(video),
                                    *opcion, "-map", "[out]",
                                    "-c:a", "libmp3lame", "-q:a", "4", str(salida)],
                                   capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                   timeout=1800)
            except subprocess.TimeoutExpired:
                sys.exit("ffmpeg tardó más de 30 minutos y lo detuve. Avísame.")
            if r.returncode == 0 or "Unrecognized option" not in r.stderr:
                break
    if r.returncode != 0:
        sys.exit(f"ffmpeg falló:\n{r.stderr[:600]}")

    nuevo = duracion(salida)

    def mmss(s):
        return f"{int(s // 60)}:{int(s % 60):02}"
    print(f"Original: {mmss(total)}  ->  Condensado: {mmss(nuevo)} "
          f"({nuevo / total:.0%} del original, {len(tramos)} tramos)")
    print(f"Listo:\n{salida}")


if __name__ == "__main__":
    main()
