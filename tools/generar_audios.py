#!/usr/bin/env python3
"""Genera los audios MP3 (voz natural de Gemini) para numeros-caperucita.html.

Uso:
  export GEMINI_API_KEY="tu_key_de_aistudio"     (Windows PowerShell: $env:GEMINI_API_KEY="...")
  python3 tools/generar_audios.py [--voice Leda] [--force]

Crea la carpeta audio/ con un archivo por palabra (ej: audio/thirty-five.mp3).
Necesita ffmpeg para MP3; sin ffmpeg guarda .wav (la app también los lee).
Solo usa la librería estándar de Python. Si Google te da error 429 espera y
vuelve a ejecutarlo: lo ya generado se salta.
"""
import argparse, base64, json, os, re, shutil, subprocess, sys, time, urllib.request, urllib.error, wave

ONES = ["","one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen"]
TENS = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]

def num_word(n):
    if n == 100: return "one hundred"
    if n < 20: return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ("-" + ONES[o] if o else "")

STORY = ["Little Red Riding Hood","wolf","wood","Grandma","mother","woodcutter","flowers","house",
         "basket","milk","bread","butter","eyes","ears","nose","mouth","teeth"]
EXTRA = ["forest","Hello! Let's practice English."]

def slug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def texts():
    seen, out = set(), []
    for t in [num_word(n).replace("-", " ") for n in range(11, 101)] + STORY + EXTRA:
        if t not in seen: seen.add(t); out.append(t)
    return out

def tts(text, voice, key):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
    prompt = "Say clearly and cheerfully, like a kind English teacher talking to a 9 year old child: " + text
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
              "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
    return base64.b64decode(j["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])

def save(pcm, path_no_ext, ffmpeg):
    wav = path_no_ext + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    if ffmpeg:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", wav, "-af", "silenceremove=1:0:-50dB,loudnorm", "-b:a", "96k", path_no_ext + ".mp3"], check=True)
        os.remove(wav)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Leda"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", default="audio")
    a = ap.parse_args()
    key = os.environ.get("GEMINI_API_KEY")
    if not key: sys.exit("Falta la variable de entorno GEMINI_API_KEY")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg: print("Aviso: no hay ffmpeg, se guardarán .wav")
    os.makedirs(a.out, exist_ok=True)
    todo = texts(); ok = fail = 0
    for i, t in enumerate(todo, 1):
        base = os.path.join(a.out, slug(t))
        if not a.force and (os.path.exists(base + ".mp3") or os.path.exists(base + ".wav")):
            ok += 1; continue
        for attempt in range(5):
            try:
                save(tts(t, a.voice, key), base, ffmpeg); ok += 1; print(f"[{i}/{len(todo)}] {t}"); break
            except urllib.error.HTTPError as e:
                if e.code == 429: print("Límite de Google, espero 25 s…"); time.sleep(25); continue
                print(f"[{i}/{len(todo)}] {t}: HTTP {e.code}"); fail += 1; break
            except Exception as e:
                print(f"[{i}/{len(todo)}] {t}: {e}"); time.sleep(3)
        else: fail += 1
        time.sleep(1)
    print(f"Listo: {ok} audios, {fail} fallaron. Subí la carpeta '{a.out}/' al repositorio.")

if __name__ == "__main__": main()
