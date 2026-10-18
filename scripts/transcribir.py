"""Paso 1: transcribe un audio o video en japonés con Soniox y deja tres archivos:

  <nombre>.soniox.json  -> respuesta completa de Soniox (por si hace falta después)
  <nombre>.ja.srt       -> subtítulos BORRADOR en japonés
  <nombre>.dudas.txt    -> partes donde Soniox no está seguro, para revisarlas con el audio

Uso:   python transcribir.py "archivo.mp4"
       python transcribir.py "archivo.mp4" --reusar   (usa el .soniox.json que ya existe:
                                                        no paga otra transcripción)
Antes: la clave debe estar en la variable de entorno SONIOX_API_KEY.
"""
import json
import os
import sys
import time
from pathlib import Path

import unicodedata

import requests

try:
    from janome.tokenizer import Tokenizer
    _JANOME = Tokenizer()
except Exception:  # sin janome el script funciona, pero corta peor
    _JANOME = None

API = "https://api.soniox.com/v1"

# Reglas de corte de subtítulos (valores de partida, se ajustan con clips reales)
PAUSA_MS = 600          # una pausa más larga que esto corta el subtítulo
MAX_CARACTERES = 24     # largo máximo de una línea
MAX_DURACION_MS = 6000  # duración máxima de un subtítulo
MIN_CARACTERES = 5      # subtítulos más cortos se pegan al vecino
MIN_DURACION_MS = 700
FIN_FRASE = "。？！?!"
ABRE = "「『（("
CIERRA = "」』）)"
PUNTUACION = "、。，．！？?!「」『』（）()・…ー—―"  # la ー no cuenta como puntuación en las reglas de dudas
# Dudas: se evalúan por tipo de carácter (los kana sueltos suelen estar bien aunque la
# confianza baje; los kanji y katakana son donde Soniox más se equivoca)
CONFIANZA_KANJI = 0.80   # kanji, katakana y números
CONFIANZA_KANA = 0.55    # hiragana
CONFIANZA_URGENTE = 0.50


def cabeceras():
    clave = os.environ.get("SONIOX_API_KEY")
    if not clave:
        sys.exit("No encuentro SONIOX_API_KEY. Revisa que guardaste la variable "
                 "y que abriste PowerShell DESPUÉS de guardarla.")
    return {"Authorization": f"Bearer {clave}"}


def revisar(resp):
    if not resp.ok:
        sys.exit(f"Soniox respondió con un error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def transcribir(ruta):
    h = cabeceras()
    print("1/4 Subiendo el archivo...")
    with open(ruta, "rb") as f:
        archivo = revisar(requests.post(f"{API}/files", headers=h,
                                        files={"file": (ruta.name, f)}))
    cuerpo = {
        "model": "stt-async-v5",
        "file_id": archivo["id"],
        "language_hints": ["ja"],
    }
    print("2/4 Pidiendo la transcripción...")
    t = revisar(requests.post(f"{API}/transcriptions", headers=h, json=cuerpo))
    print("3/4 Esperando el resultado...")
    while True:
        estado = revisar(requests.get(f"{API}/transcriptions/{t['id']}", headers=h))
        if estado["status"] == "completed":
            break
        if estado["status"] == "error":
            sys.exit(f"Soniox no pudo transcribir: {estado.get('error_message')}")
        time.sleep(2)
    print("4/4 Descargando el texto...")
    resultado = revisar(requests.get(f"{API}/transcriptions/{t['id']}/transcript", headers=h))
    # Limpieza: borra el archivo y la transcripción de los servidores de Soniox
    requests.delete(f"{API}/transcriptions/{t['id']}", headers=h)
    requests.delete(f"{API}/files/{archivo['id']}", headers=h)
    verificar_borrado(h, t["id"], archivo["id"])
    return resultado


def verificar_borrado(h, id_transcripcion, id_archivo):
    """Pregunta a Soniox qué le queda guardado y confirma que ya no está nuestro clip."""
    try:
        archivos = requests.get(f"{API}/files", headers=h, timeout=30).json().get("files", [])
        trans = requests.get(f"{API}/transcriptions", headers=h, timeout=30).json().get(
            "transcriptions", [])
        sigue_archivo = any(a["id"] == id_archivo for a in archivos)
        sigue_trans = any(x["id"] == id_transcripcion for x in trans)
        if sigue_archivo or sigue_trans:
            print("AVISO: Soniox todavía guarda "
                  f"{'el archivo' if sigue_archivo else ''}"
                  f"{' y ' if sigue_archivo and sigue_trans else ''}"
                  f"{'la transcripción' if sigue_trans else ''}. "
                  "Avísame para revisarlo.")
        else:
            print(f"Borrado confirmado. A Soniox le quedan {len(archivos)} archivos "
                  f"y {len(trans)} transcripciones guardadas en tu cuenta.")
    except Exception as error:  # la comprobación nunca debe tumbar el resultado
        print(f"No pude comprobar el borrado ({error}). Tu transcripción sí se guardó.")


def hora_srt(ms):
    ms = int(round(ms))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def tokens_validos(resultado):
    return [t for t in resultado["tokens"]
            if t.get("text", "").strip() and "start_ms" in t and "end_ms" in t]


def tipo(caracter):
    """'punt', 'kana', 'kanji' (incluye katakana y números) u 'otro'."""
    if caracter in PUNTUACION and caracter != "ー":
        return "punt"
    nombre = unicodedata.name(caracter, "")
    if "HIRAGANA" in nombre or caracter == "ー":
        return "kana"
    if "KATAKANA" in nombre or "CJK" in nombre or "DIGIT" in nombre:
        return "kanji"
    return "otro"


# ---------- Cortes: primero en unidades naturales (bunsetsu), luego en subtítulos ----------

def unidades(tokens):
    """Agrupa los tokens en unidades de lectura (una palabra con sus partículas)."""
    texto = "".join(t["text"] for t in tokens)
    dueno = []  # carácter -> índice del token
    for i, t in enumerate(tokens):
        dueno.extend([i] * len(t["text"]))
    if _JANOME is None:
        grupos = [[i] for i in range(len(tokens))]
    else:
        grupos, actual, pos = [], [], 0
        tras_fin_de_frase = False
        for m in _JANOME.tokenize(texto):
            largo = len(m.surface)
            idx = sorted(set(dueno[pos:pos + largo]))
            pos += largo
            categoria = m.part_of_speech.split(",")
            principal, detalle = categoria[0], categoria[1]
            es_apoyo = (principal in ("助詞", "助動詞") or detalle in ("接尾", "非自立")
                        or (principal == "記号" and m.surface not in ABRE))
            # tras un punto, lo siguiente siempre abre unidad nueva (janome confunde a veces
            # el "で" que inicia frase con una terminación verbal)
            abre_unidad = (not es_apoyo) or (tras_fin_de_frase and m.surface not in CIERRA
                                             and m.surface not in FIN_FRASE)
            if actual and abre_unidad and not (tokens[actual[-1]]["text"] in ABRE):
                grupos.append(actual)
                actual = []
            if m.surface in FIN_FRASE:
                tras_fin_de_frase = True
            elif m.surface not in CIERRA:
                tras_fin_de_frase = False
            for i in idx:
                if i not in actual and not any(i in g for g in grupos):
                    actual.append(i)
        if actual:
            grupos.append(actual)
    salida = []
    for g in grupos:
        if not g:
            continue
        ts = [tokens[i] for i in g]
        salida.append({"tokens": ts,
                       "texto": "".join(t["text"] for t in ts),
                       "ini": ts[0]["start_ms"], "fin": ts[-1]["end_ms"]})
    return salida


def cortar(tokens):
    """Devuelve una lista de subtítulos; cada uno es una lista de tokens."""
    us = unidades(tokens)
    cues, actual = [], []

    def cerrar():
        if actual:
            cues.append([t for u in actual for t in u["tokens"]])
            actual.clear()

    for u in us:
        if actual:
            pausa = u["ini"] - actual[-1]["fin"]
            largo = sum(len(x["texto"]) for x in actual) + len(u["texto"])
            duracion = u["fin"] - actual[0]["ini"]
            if pausa >= PAUSA_MS or largo > MAX_CARACTERES or duracion > MAX_DURACION_MS:
                cerrar()
        actual.append(u)
        fin = u["texto"].rstrip(CIERRA)
        if fin and fin[-1] in FIN_FRASE:
            cerrar()
        elif fin.endswith("、") and sum(len(x["texto"]) for x in actual) >= 12:
            cerrar()
    cerrar()
    return pegar_huerfanos(cues)


def largo_cue(cue):
    return sum(len(t["text"]) for t in cue)


def pegar_huerfanos(cues):
    """Subtítulos demasiado cortos o rápidos se unen al vecino más cercano en el tiempo."""
    cambio = True
    while cambio and len(cues) > 1:
        cambio = False
        for i, c in enumerate(cues):
            dur = c[-1]["end_ms"] - c[0]["start_ms"]
            if largo_cue(c) >= MIN_CARACTERES and dur >= MIN_DURACION_MS:
                continue
            ant = cues[i - 1] if i > 0 else None
            sig = cues[i + 1] if i + 1 < len(cues) else None
            gap_a = c[0]["start_ms"] - ant[-1]["end_ms"] if ant else 10**9
            gap_s = sig[0]["start_ms"] - c[-1]["end_ms"] if sig else 10**9
            # solo se une si la pausa es corta y el resultado no queda enorme
            # un fragmento que abre una frase nueva (el anterior terminó en 。) va con el siguiente
            if ant and texto_de(ant).rstrip(CIERRA)[-1:] in FIN_FRASE and sig and gap_s < 1000:
                gap_a = 10**9
            if gap_a <= gap_s and gap_a < 1000 and largo_cue(ant) + largo_cue(c) <= MAX_CARACTERES + 10:
                ant.extend(c)
                del cues[i]
                cambio = True
                break
            if gap_s < 1000 and sig and largo_cue(sig) + largo_cue(c) <= MAX_CARACTERES + 10:
                sig[:0] = c
                del cues[i]
                cambio = True
                break
    return cues


def texto_de(cue):
    return "".join(t["text"] for t in cue).strip()


def escribir_srt(cues, destino):
    bloques = []
    for i, cue in enumerate(cues, 1):
        bloques.append(f"{i}\n{hora_srt(cue[0]['start_ms'])} --> "
                       f"{hora_srt(cue[-1]['end_ms'])}\n{texto_de(cue)}\n")
    destino.write_text("\n".join(bloques), encoding="utf-8")


# ---------- Dudas: por palabra, con el pasaje marcado ----------

def es_duda(t):
    c = t.get("confidence", 1)
    if c < CONFIANZA_URGENTE:
        return tipo(t["text"][0]) != "punt"
    t0 = tipo(t["text"][0])
    if t0 == "kanji":
        return c < CONFIANZA_KANJI
    if t0 == "kana":
        return c < CONFIANZA_KANA
    return False


def marcar(cue):
    """Devuelve (texto con 【dudas】, lista de (palabra, confianza mínima))."""
    partes, dudas, tramo = [], [], []

    def cerrar():
        if tramo:
            palabra = "".join(t["text"] for t in tramo)
            partes.append(f"【{palabra}】")
            dudas.append((palabra, min(t["confidence"] for t in tramo)))
            tramo.clear()

    for t in cue:
        if es_duda(t):
            tramo.append(t)
        else:
            cerrar()
            partes.append(t["text"])
    cerrar()
    return "".join(partes).strip(), dudas


def escribir_dudas(cues, destino):
    items = []
    for i, cue in enumerate(cues, 1):
        marcado, dudas = marcar(cue)
        if dudas:
            minimo = min(c for _, c in dudas)
            items.append((i, cue[0]["start_ms"], marcado, dudas, minimo))
    urgentes = [x for x in items if x[4] < CONFIANZA_URGENTE]
    resto = [x for x in items if x[4] >= CONFIANZA_URGENTE]

    def linea(x):
        i, ini, marcado, dudas, _ = x
        lista = ", ".join(f"{p} ({c:.0%})" for p, c in dudas)
        return f"Subtítulo {i} [{hora_srt(ini)[:8]}]\n    {marcado}\n    revisar: {lista}\n"

    texto = [f"Las partes entre 【 】 son las que Soniox no tiene claras. "
             f"Revisa primero las urgentes (menos de {CONFIANZA_URGENTE:.0%} de confianza).\n"]
    texto.append(f"=== URGENTES ({len(urgentes)}) ===\n")
    texto.extend(linea(x) for x in urgentes) if urgentes else texto.append("(ninguna)\n")
    texto.append(f"=== OTRAS DUDAS ({len(resto)}) ===\n")
    texto.extend(linea(x) for x in resto) if resto else texto.append("(ninguna)\n")
    destino.write_text("\n".join(texto), encoding="utf-8")
    return len(items), len(urgentes)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a != "--reusar"]
    reusar = "--reusar" in sys.argv[1:]
    if len(args) != 1:
        sys.exit('Uso: python transcribir.py "archivo.mp4" [--reusar]')
    ruta = Path(args[1 - 1])
    if not ruta.is_file():
        sys.exit(f"No encuentro el archivo: {ruta}")
    base = ruta.with_suffix("")
    ruta_json = ruta.with_name(base.name + ".soniox.json")
    if reusar and ruta_json.is_file():
        print("Usando la transcripción guardada (no se paga otra vez).")
        resultado = json.loads(ruta_json.read_text(encoding="utf-8"))
    else:
        resultado = transcribir(ruta)
        ruta_json.write_text(json.dumps(resultado, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    if _JANOME is None:
        print("AVISO: falta 'janome'; los cortes serán menos naturales. "
              "Instálalo con: python -m pip install janome")
    cues = cortar(tokens_validos(resultado))
    escribir_srt(cues, ruta.with_name(base.name + ".ja.srt"))
    n, urgentes = escribir_dudas(cues, ruta.with_name(base.name + ".dudas.txt"))
    print(f"\nListo: {len(cues)} subtítulos; {n} con dudas ({urgentes} urgentes).")
    print("Se crearon tres archivos nuevos junto a tu clip. El original no se tocó.")


if __name__ == "__main__":
    main()
