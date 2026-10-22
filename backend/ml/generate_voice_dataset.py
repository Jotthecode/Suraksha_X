"""
Builds the SurakshaX voice-distress keyword dataset.

Output: backend/ml/data/voice/<class>/*.wav  (1.0 s, 16 kHz, mono, 16-bit PCM)
        backend/ml/data/voice/metadata.csv  (path, class, voice, raw_id, text, kind)

Speech source: Microsoft neural voices via `edge-tts` (free, needs internet).
Fallback: Windows SAPI (System.Speech) through PowerShell if edge-tts fails.
Raw TTS output is cached in backend/ml/data/tts_cache/ so reruns are fast.

Usage (from anywhere):
    python backend/ml/generate_voice_dataset.py            # full build
    python backend/ml/generate_voice_dataset.py --quick    # small smoke build
"""

import argparse
import asyncio
import csv
import hashlib
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from ml.features import SAMPLE_RATE, WINDOW_SAMPLES  # noqa: E402
from ml.audio_io import decode_audio, write_wav  # noqa: E402
from ml import augment as A  # noqa: E402

DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(DATA_DIR, "voice")
CACHE_DIR = os.path.join(DATA_DIR, "tts_cache")

CLASSES = ["help", "save_me", "emergency", "bachao", "madad_karo", "madat_kara",
           "vachva", "kapaathu", "sahajjo_koro", "background"]
KEYWORD_CLASSES = CLASSES[:-1]

# ------------------------------------------------------------------ voices
VOICES = [
    "en-IN-NeerjaNeural", "en-IN-NeerjaExpressiveNeural", "en-IN-PrabhatNeural",
    "en-US-AvaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural", "en-US-BrianNeural",
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural", "en-US-ChristopherNeural",
    "en-US-EricNeural", "en-US-MichelleNeural", "en-US-RogerNeural", "en-US-SteffanNeural",
    "en-US-AnaNeural",
    "en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural",
    "en-US-EmmaMultilingualNeural", "en-US-BrianMultilingualNeural",
    "en-GB-LibbyNeural", "en-GB-MaisieNeural", "en-GB-RyanNeural", "en-GB-SoniaNeural",
    "en-GB-ThomasNeural",
    "hi-IN-MadhurNeural", "hi-IN-SwaraNeural",
    "mr-IN-AarohiNeural", "mr-IN-ManoharNeural",
    "ta-IN-PallaviNeural", "ta-IN-ValluvarNeural",
    "bn-IN-BashkarNeural", "bn-IN-TanishaaNeural",
    "gu-IN-DhwaniNeural", "gu-IN-NiranjanNeural",
    "te-IN-MohanNeural", "te-IN-ShrutiNeural",
    "kn-IN-GaganNeural", "kn-IN-SapnaNeural",
    "ml-IN-MidhunNeural", "ml-IN-SobhanaNeural",
    "ur-IN-GulNeural", "ur-IN-SalmanNeural",
]
# Entire speakers held out for the speaker-generalisation test set.
HELDOUT_VOICES = ["hi-IN-SwaraNeural", "en-GB-RyanNeural", "ta-IN-ValluvarNeural"]


def voice_lang(voice):
    if "Multilingual" in voice:
        return "multi"
    return voice.split("-")[0]


# ------------------------------------------------------------------ texts
KEYWORD_TEXTS = {
    "help": {
        "roman": ["help", "Help!", "help help", "HELP!", "help me", "Help! Help!"],
        "native": {"hi": ["हेल्प", "हेल्प!"], "mr": ["हेल्प!"], "multi": ["help!!", "help, help"]},
    },
    "save_me": {
        "roman": ["save me", "Save me!", "please save me", "SAVE ME!", "someone save me"],
        "native": {"multi": ["save me!!", "please, save me"]},
    },
    "emergency": {
        "roman": ["emergency", "Emergency!", "it's an emergency", "EMERGENCY!", "emergency emergency"],
        "native": {"hi": ["इमरजेंसी", "इमरजेंसी है!"], "mr": ["इमर्जन्सी!"], "multi": ["Emergency!!"]},
    },
    "bachao": {
        "roman": ["bachao", "Bachao!!", "bachao bachao", "BACHAO!", "mujhe bachao", "bachaao"],
        "native": {"hi": ["बचाओ", "बचाओ!", "बचाओ बचाओ", "मुझे बचाओ!", "कोई बचाओ"],
                   "mr": ["बचाओ!", "बचाओ बचाओ"], "multi": ["बचाओ!", "बचाओ बचाओ!"],
                   "bn": ["বাঁচাও!", "বাঁচাও"], "ur": ["بچاؤ!", "بچاؤ بچاؤ"], "gu": ["બચાઓ!"]},
    },
    "madad_karo": {
        "roman": ["madad karo", "Madad karo!", "koi madad karo", "MADAD KARO!", "meri madad karo"],
        "native": {"hi": ["मदद करो", "मदद करो!", "कोई मदद करो!", "मेरी मदद करो"],
                   "mr": ["मदद करो!"], "multi": ["मदद करो!", "कोई मदद करो"],
                   "ur": ["مدد کرو!", "میری مدد کرو"]},
    },
    "madat_kara": {
        "roman": ["madat kara", "Madat kara!", "koni tari madat kara", "MADAT KARA!"],
        "native": {"mr": ["मदत करा", "मदत करा!", "कोणीतरी मदत करा!", "माझी मदत करा"],
                   "hi": ["मदत करा!", "मदत करा"], "multi": ["मदत करा!"]},
    },
    "vachva": {
        "roman": ["vachva", "Vachva!", "vachva vachva", "mala vachva", "VACHVA!"],
        "native": {"mr": ["वाचवा", "वाचवा!", "मला वाचवा!", "वाचवा वाचवा"],
                   "hi": ["वाचवा!", "वाचवा"], "multi": ["वाचवा!"]},
    },
    "kapaathu": {
        "roman": ["kapaathu", "Kaapaathu!", "kaapaathunga", "KAPAATHU!", "ennai kaapaathu"],
        "native": {"ta": ["காப்பாத்து", "காப்பாத்து!", "காப்பாத்துங்க!", "என்னை காப்பாத்து"],
                   "ml": ["കാപ്പാത്ത്!"], "multi": ["காப்பாத்து!"]},
    },
    "sahajjo_koro": {
        "roman": ["sahajjo koro", "Shahajjo koro!", "amake sahajjo koro", "SAHAJJO KORO!"],
        "native": {"bn": ["সাহায্য করো", "সাহায্য করো!", "আমাকে সাহায্য করো!", "কেউ সাহায্য করো"],
                   "multi": ["সাহায্য করো!"]},
    },
}

BACKGROUND_TEXTS = {
    "en": [
        "hello how are you", "let's go home", "what time is it", "good morning", "good night",
        "thank you very much", "see you tomorrow", "I am fine", "where is the bus stop",
        "call me later", "the weather is nice today", "one two three four", "five six seven eight",
        "nine ten eleven twelve", "my name is Priya", "Rahul", "Ananya", "Vikram", "Sneha",
        "open the door", "turn on the light", "helmet", "healthy", "hello", "yellow", "safe",
        "same", "shave", "seven", "energy", "merchant", "emerald", "saving", "say it again",
        "how much does it cost", "I like this song", "let's have coffee", "the train is late",
        "send me the file", "happy birthday", "where are my keys", "I'm going to the office",
        "please sit down", "wait for me", "it's raining", "nice to meet you", "pass the salt",
        "the meeting starts at ten", "can you hear me", "okay sure", "no problem", "maybe later",
    ],
    "hi_roman": [
        "kya haal hai", "chalo", "bachpan", "madam", "khana kha liya", "kahan ja rahe ho",
        "theek hai", "namaste", "shukriya", "paani do", "bahut accha", "ghar chalo",
        "aaj mausam accha hai", "mera naam Priya hai", "bazaar chalein", "bachche", "badal",
        "maidan", "ek do teen chaar", "kal milte hain", "chai piyoge", "kitne baje hain",
        "kaisa hai", "kasa aahes", "mi ghari jaat aahe", "vanakkam", "kaapi", "kemon acho",
        "dhonnobad", "sahitya", "vachan", "madhur", "bachat", "madarsa", "chalo chalte hain",
    ],
    "hi": ["क्या हाल है", "चलो", "बचपन", "मैडम", "नमस्ते", "ठीक है", "बच्चे", "मौसम अच्छा है",
           "खाना खा लिया", "एक दो तीन चार", "कल मिलते हैं", "चाय पियोगे", "बचत करो", "मदरसा",
           "कितने बजे हैं", "घर चलो", "बहुत अच्छा", "धन्यवाद"],
    "mr": ["कसा आहेस", "मी घरी जातो", "चल", "वाचन", "नमस्कार", "जेवण झालं का", "उद्या भेटू",
           "एक दोन तीन चार", "छान आहे", "मदन", "किती वाजले", "पाऊस पडतोय", "चला जाऊया"],
    "ta": ["வணக்கம்", "எப்படி இருக்கீங்க", "சாப்பிட்டீங்களா", "காபி", "போகலாம்", "நன்றி",
           "ஒன்று இரண்டு மூன்று", "நாளை பார்க்கலாம்", "மழை பெய்கிறது", "சரி"],
    "bn": ["কেমন আছো", "ধন্যবাদ", "সাহিত্য", "চলো", "বাড়ি যাব", "এক দুই তিন", "শুভ সকাল",
           "আজ আবহাওয়া ভালো", "ঠিক আছে", "চা খাবে"],
    "gu": ["કેમ છો", "આભાર", "ચાલો", "એક બે ત્રણ", "સુપ્રભાત", "ઘરે જઈએ", "બચત"],
    "te": ["ఎలా ఉన్నారు", "ధన్యవాదాలు", "వెళ్దాం", "ఒకటి రెండు మూడు", "శుభోదయం", "సరే"],
    "kn": ["ಹೇಗಿದ್ದೀರಾ", "ಧನ್ಯವಾದ", "ಹೋಗೋಣ", "ಒಂದು ಎರಡು ಮೂರು", "ಶುಭೋದಯ", "ಸರಿ"],
    "ml": ["സുഖമാണോ", "നന്ദി", "പോകാം", "ഒന്ന് രണ്ട് മൂന്ന്", "സുപ്രഭാതം", "ശരി", "കാപ്പി"],
    "ur": ["کیا حال ہے", "شکریہ", "چلو", "ٹھیک ہے", "ایک دو تین", "صبح بخیر"],
}

NATIVE_SHARE = {"hi": ["hi", "mr"], "mr": ["mr", "hi"], "multi": ["multi"], "ta": ["ta"], "bn": ["bn"],
                "ur": ["ur"], "gu": ["gu"], "ml": ["ml"], "te": [], "kn": [], "en": []}


def keyword_candidates(cls, voice):
    lang = voice_lang(voice)
    spec = KEYWORD_TEXTS[cls]
    native = []
    for l in NATIVE_SHARE.get(lang, []):
        native += spec["native"].get(l, [])
    return list(spec["roman"]), native


def background_candidates(voice):
    lang = voice_lang(voice)
    texts = list(BACKGROUND_TEXTS["en"]) + list(BACKGROUND_TEXTS["hi_roman"])
    if lang == "multi":
        texts += BACKGROUND_TEXTS["hi"]
    elif lang in BACKGROUND_TEXTS:
        texts += BACKGROUND_TEXTS[lang] * 2  # favour native phrases for Indic voices
    if lang == "mr":
        texts += BACKGROUND_TEXTS["hi"]
    return texts


def prosody(rng, shouted):
    if shouted:
        rate = int(rng.integers(5, 26))
        pitch = int(rng.integers(3, 16))
        vol = int(rng.integers(10, 51))
    else:
        rate = int(rng.integers(-20, 26))
        pitch = int(rng.integers(-15, 16))
        vol = int(rng.integers(-20, 21))
    return f"{rate:+d}%", f"{pitch:+d}Hz", f"{vol:+d}%"


def make_requests(args):
    """Return list of TTS request dicts (deterministic)."""
    rng = np.random.default_rng(2026)
    reqs = []
    voices = VOICES if not args.quick else VOICES[::4] + HELDOUT_VOICES
    for voice in voices:
        for cls in KEYWORD_CLASSES:
            roman, native = keyword_candidates(cls, voice)
            n_native = min(len(native), 2 if not args.quick else 1)
            n_roman = (4 - n_native) if not args.quick else 1
            chosen = list(rng.choice(roman, size=min(n_roman, len(roman)), replace=False))
            if n_native:
                chosen += list(rng.choice(native, size=n_native, replace=False))
            for text in chosen:
                shouted = "!" in text or text.isupper()
                for _ in range(args.prosody_variants):
                    rate, pitch, vol = prosody(rng, shouted)
                    reqs.append(dict(cls=cls, voice=voice, text=str(text), rate=rate, pitch=pitch, volume=vol))
        bg = background_candidates(voice)
        n_bg = args.bg_per_voice if not args.quick else 4
        for text in rng.choice(bg, size=min(n_bg, len(bg)), replace=False):
            rate, pitch, vol = prosody(rng, False)
            reqs.append(dict(cls="background", voice=voice, text=str(text), rate=rate, pitch=pitch, volume=vol))
    for r in reqs:
        key = "|".join([r["voice"], r["text"], r["rate"], r["pitch"], r["volume"]])
        r["raw_id"] = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        r["cache"] = os.path.join(CACHE_DIR, r["raw_id"] + ".mp3")
    return reqs


# ------------------------------------------------------------------ edge-tts
async def _edge_one(sem, r, stats):
    import edge_tts
    if os.path.exists(r["cache"]) and os.path.getsize(r["cache"]) > 500:
        stats["cached"] += 1
        return True
    async with sem:
        for attempt in range(4):
            try:
                comm = edge_tts.Communicate(r["text"], r["voice"], rate=r["rate"],
                                            pitch=r["pitch"], volume=r["volume"])
                tmp = r["cache"] + ".part"
                await asyncio.wait_for(comm.save(tmp), timeout=40)
                if os.path.getsize(tmp) > 500:
                    os.replace(tmp, r["cache"])
                    stats["ok"] += 1
                    return True
                os.remove(tmp)
            except Exception as e:  # network / throttling
                stats["last_error"] = repr(e)[:200]
                await asyncio.sleep(1.5 * (attempt + 1))
        stats["failed"] += 1
        return False


async def _edge_all(reqs, concurrency):
    sem = asyncio.Semaphore(concurrency)
    stats = {"ok": 0, "cached": 0, "failed": 0, "last_error": None}
    tasks = [_edge_one(sem, r, stats) for r in reqs]
    done = 0
    t0 = time.time()
    results = []
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)
        done += 1
        if done % 250 == 0 or done == len(tasks):
            print(f"  edge-tts {done}/{len(tasks)}  ok={stats['ok']} cached={stats['cached']} "
                  f"failed={stats['failed']}  {time.time() - t0:.0f}s", flush=True)
    return stats


def run_edge_tts(reqs, concurrency=12):
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("edge-tts not installed")
        return {"ok": 0, "cached": 0, "failed": len(reqs), "last_error": "edge-tts not installed"}
    return asyncio.run(_edge_all(reqs, concurrency))


# ------------------------------------------------------------------ SAPI fallback
def run_sapi_fallback(n_texts_per_class=6):
    """Synthesize romanized keywords + English background with installed Windows SAPI voices."""
    if os.name != "nt":
        return []
    rng = np.random.default_rng(7)
    sapi_dir = os.path.join(CACHE_DIR, "sapi")
    os.makedirs(sapi_dir, exist_ok=True)
    jobs = []
    for cls in KEYWORD_CLASSES:
        for text in KEYWORD_TEXTS[cls]["roman"][:n_texts_per_class]:
            jobs.append((cls, text))
    for text in BACKGROUND_TEXTS["en"] + BACKGROUND_TEXTS["hi_roman"]:
        jobs.append(("background", text))
    lines = ["Add-Type -AssemblyName System.Speech",
             "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
             "$voices = $s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"]
    reqs = []
    for i, (cls, text) in enumerate(jobs):
        for rate in rng.choice([-3, -1, 0, 2, 4], size=2, replace=False):
            fid = hashlib.sha1(f"sapi|{text}|{rate}".encode()).hexdigest()[:16]
            reqs.append(dict(cls=cls, text=text, rate=int(rate), fid=fid))
    safe = lambda t: t.replace("'", "''")
    lines.append("foreach ($v in $voices) { $s.SelectVoice($v)")
    for r in reqs:
        lines.append(f" $p = Join-Path '{sapi_dir}' (($v -replace '[^A-Za-z]','') + '__{r['fid']}.wav');"
                     f" if (-not (Test-Path $p)) {{ $s.Rate = {r['rate']}; $s.SetOutputToWaveFile($p);"
                     f" $s.Speak('{safe(r['text'])}') }}")
    lines.append("}; $s.SetOutputToNull(); $voices -join ','")
    ps = os.path.join(sapi_dir, "gen.ps1")
    with open(ps, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps],
                             capture_output=True, text=True, timeout=1800)
        names = [n for n in out.stdout.strip().split(",") if n]
    except Exception as e:
        print("SAPI fallback failed:", e)
        return []
    results = []
    for name in names:
        tag = "sapi-" + "".join(c for c in name if c.isalpha())
        for r in reqs:
            p = os.path.join(sapi_dir, "".join(c for c in name if c.isalpha()) + "__" + r["fid"] + ".wav")
            if os.path.exists(p):
                results.append(dict(cls=r["cls"], voice=tag, text=r["text"], raw_id=tag + r["fid"],
                                    cache=p, rate=str(r["rate"]), pitch="0", volume="0"))
    print(f"SAPI fallback produced {len(results)} clips from voices: {names}")
    return results


# ------------------------------------------------------------------ augmentation workers
_POOL = None


def _init_worker(pool):
    global _POOL
    _POOL = pool


def _augment_job(job):
    """job = (out_path, speech(np.ndarray) | None, kind, seed, keyword)"""
    out_path, speech, kind, seed, keyword = job
    rng = np.random.default_rng(seed)
    n = WINDOW_SAMPLES
    if kind == "speech":
        x = A.augment_clip(speech, rng, _POOL, keyword=keyword)
    elif kind == "noise":
        noise, _ = A.random_noise(n, rng, _POOL)
        if rng.random() < 0.3:
            noise = A.lowpass(noise, rng.uniform(1000, 6000))
        x = noise / (np.max(np.abs(noise)) + 1e-9) * 10 ** (rng.uniform(-40, -3) / 20)
    elif kind == "babble":
        x = A.babble_noise(n, rng, _POOL, k=int(rng.integers(2, 8)))
        if rng.random() < 0.5:
            x = A.reverb(x, rng)
        if rng.random() < 0.5:
            x = A.add_noise(x, A.random_noise(n, rng, _POOL)[0], rng.uniform(0, 20))
        x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (rng.uniform(-30, -3) / 20)
    else:  # silence / near-silence (mic hiss, room tone)
        x = A.white_noise(n, rng) * 10 ** (rng.uniform(-90, -50) / 20)
        if rng.random() < 0.5:
            x = A.lowpass(x, rng.uniform(500, 4000)) + A.brown_noise(n, rng) * 10 ** (rng.uniform(-80, -55) / 20)
    write_wav(out_path, np.asarray(x, dtype=np.float32))
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="tiny dataset for pipeline testing")
    ap.add_argument("--prosody-variants", type=int, default=2)
    ap.add_argument("--bg-per-voice", type=int, default=20)
    ap.add_argument("--keyword-target", type=int, default=420, help="augmented clips per keyword class")
    ap.add_argument("--bg-target", type=int, default=1900, help="augmented clips in background class")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--force-sapi", action="store_true")
    args = ap.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    reqs = make_requests(args)
    print(f"{len(reqs)} TTS requests across {len(set(r['voice'] for r in reqs))} voices")

    stats = {"ok": 0, "cached": 0, "failed": len(reqs)}
    if not args.force_sapi:
        stats = run_edge_tts(reqs, args.concurrency)
        print("edge-tts stats:", stats)
    good = [r for r in reqs if os.path.exists(r["cache"]) and os.path.getsize(r["cache"]) > 500]
    if args.force_sapi or len(good) < 0.5 * len(reqs):
        print("edge-tts unavailable or mostly failing -> using Windows SAPI fallback")
        good += run_sapi_fallback()
    if not good:
        sys.exit("No TTS audio could be produced (no network for edge-tts and no SAPI).")

    # decode + trim
    print("decoding TTS audio ...")
    raw = []
    for r in good:
        try:
            x = decode_audio(r["cache"])
            x = A.trim(x)
            if x.size < 1600:
                continue
            x = x / (np.max(np.abs(x)) + 1e-9) * 0.8
            raw.append((r, x.astype(np.float32)))
        except Exception as e:
            print("  decode failed", r["cache"], e)
    print(f"decoded {len(raw)} clips")

    babble_pool = [x for r, x in raw if r["cls"] == "background" and r["voice"] not in HELDOUT_VOICES]

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    for c in CLASSES:
        os.makedirs(os.path.join(OUT_DIR, c), exist_ok=True)

    jobs, meta = [], []
    by_cls = {c: [(r, x) for r, x in raw if r["cls"] == c] for c in CLASSES}
    kw_target = args.keyword_target if not args.quick else 60
    for c in KEYWORD_CLASSES:
        items = by_cls[c]
        if not items:
            continue
        copies = max(1, math.ceil(kw_target / len(items)))
        for r, x in items:
            for k in range(copies):
                name = f"{r['voice']}__{r['raw_id']}__{k}.wav"
                p = os.path.join(OUT_DIR, c, name)
                seed = int(r["raw_id"][:8], 16) + 1000003 * k
                jobs.append((p, x, "speech", seed, True))
                meta.append(dict(path=os.path.relpath(p, OUT_DIR), cls=c, voice=r["voice"],
                                 raw_id=r["raw_id"], text=r["text"], kind="tts_keyword"))

    bg_target = args.bg_target if not args.quick else 200
    bg_items = by_cls["background"]
    n_tts_bg = int(bg_target * 0.6)
    copies = max(1, math.ceil(n_tts_bg / max(1, len(bg_items))))
    for r, x in bg_items:
        for k in range(copies):
            name = f"{r['voice']}__{r['raw_id']}__{k}.wav"
            p = os.path.join(OUT_DIR, "background", name)
            jobs.append((p, x, "speech", int(r["raw_id"][:8], 16) + 7919 * k, False))
            meta.append(dict(path=os.path.relpath(p, OUT_DIR), cls="background", voice=r["voice"],
                             raw_id=r["raw_id"], text=r["text"], kind="tts_background"))
    n_rest = max(0, bg_target - len(bg_items) * copies)
    synth = [("noise", int(n_rest * 0.5)), ("babble", int(n_rest * 0.3)), ("silence", max(60, int(n_rest * 0.2)))]
    for kind, n in synth:
        for i in range(n):
            rid = f"{kind}{i:05d}"
            p = os.path.join(OUT_DIR, "background", f"synthetic__{rid}__0.wav")
            jobs.append((p, None, kind, 99991 * (i + 1) + len(kind), False))
            meta.append(dict(path=os.path.relpath(p, OUT_DIR), cls="background", voice="synthetic",
                             raw_id=rid, text="", kind=kind))

    print(f"augmenting -> {len(jobs)} clips with {args.workers} workers ...")
    t0 = time.time()
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker,
                                 initargs=(babble_pool,)) as ex:
            for i, _ in enumerate(ex.map(_augment_job, jobs, chunksize=16)):
                if (i + 1) % 1000 == 0:
                    print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    else:
        _init_worker(babble_pool)
        for i, j in enumerate(jobs):
            _augment_job(j)
    print(f"augmentation done in {time.time() - t0:.0f}s")

    with open(os.path.join(OUT_DIR, "metadata.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "cls", "voice", "raw_id", "text", "kind"])
        w.writeheader()
        w.writerows(meta)

    counts = {c: sum(1 for m in meta if m["cls"] == c) for c in CLASSES}
    print("clips per class:", counts)
    print("voices:", sorted(set(m["voice"] for m in meta)))


if __name__ == "__main__":
    main()
