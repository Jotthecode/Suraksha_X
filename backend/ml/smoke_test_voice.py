"""
Smoke test for the deployed voice CNN (backend/models/voice_cnn.onnx).

Synthesizes two fresh clips with a speaker that was HELD OUT of training
(hi-IN-SwaraNeural via edge-tts; falls back to Windows SAPI if offline):
  1. "bachao"        -> saved as .wav,          must trigger SOS
  2. "good morning"  -> encoded to .m4a (AAC),   must NOT trigger
then runs voice_engine.get_voice_classifier().classify_audio_file() on both,
and also exercises classify_audio_bytes() with the m4a payload.

Usage: python backend/ml/smoke_test_voice.py
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from ml.audio_io import decode_audio, encode_with_av, write_wav  # noqa: E402

VOICE = "hi-IN-SwaraNeural"  # held out from training (see generate_voice_dataset.HELDOUT_VOICES)


def tts(text, out_mp3, rate="+5%", pitch="+0Hz"):
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch).save(out_mp3))
        return decode_audio(out_mp3), f"edge-tts:{VOICE}"
    except Exception as e:
        print("edge-tts failed (", e, ") -> SAPI fallback")
        wav = out_mp3.replace(".mp3", ".wav")
        ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
              f"$s.SetOutputToWaveFile('{wav}'); $s.Speak('{text}'); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
        return decode_audio(wav), "sapi"


def main():
    from voice_engine import get_voice_classifier
    clf = get_voice_classifier()
    tmp = tempfile.mkdtemp(prefix="surakshax_smoke_")
    rng = np.random.default_rng(0)

    # clip 1: "bachao" with mild street-like noise, 2 s total, as WAV
    speech, src1 = tts("Bachao!", os.path.join(tmp, "bachao.mp3"))
    clip = np.zeros(32000, np.float32)
    s = speech[:24000]
    clip[4000:4000 + s.size] = s
    clip += rng.standard_normal(clip.size).astype(np.float32) * 0.01
    wav_path = os.path.join(tmp, "bachao.wav")
    write_wav(wav_path, clip)

    # clip 2: "good morning" as AAC .m4a
    speech2, src2 = tts("good morning", os.path.join(tmp, "good_morning.mp3"))
    clip2 = np.zeros(max(32000, speech2.size + 8000), np.float32)
    clip2[4000:4000 + speech2.size] = speech2
    clip2 += rng.standard_normal(clip2.size).astype(np.float32) * 0.01
    m4a_path = os.path.join(tmp, "good_morning.m4a")
    with open(m4a_path, "wb") as f:
        f.write(encode_with_av(clip2, "mp4", "aac", bit_rate=48000))

    keys = ["source", "sos_triggered", "posterior_probability", "detected_keyword", "language",
            "noise_condition", "snr_db", "rms_level", "windows_evaluated", "audio_duration_s",
            "inference_latency_ms", "top_candidate"]
    ok = True
    r1 = clf.classify_audio_file(wav_path)
    print(f"\n[1] {os.path.basename(wav_path)} ({src1}, text 'Bachao!')")
    print(json.dumps({k: r1.get(k) for k in keys}, indent=2, ensure_ascii=False))
    print("    class_probabilities:", r1.get("class_probabilities"))
    ok &= r1["sos_triggered"] is True and r1["detected_keyword"] == "BACHAO"

    r2 = clf.classify_audio_file(m4a_path)
    print(f"\n[2] {os.path.basename(m4a_path)} ({src2}, text 'good morning', AAC)")
    print(json.dumps({k: r2.get(k) for k in keys}, indent=2, ensure_ascii=False))
    print("    class_probabilities:", r2.get("class_probabilities"))
    ok &= r2["sos_triggered"] is False

    with open(m4a_path, "rb") as f:
        r3 = clf.classify_audio_bytes(f.read(), suffix=".m4a")
    print(f"\n[3] classify_audio_bytes(m4a) -> sos_triggered={r3['sos_triggered']} "
          f"P={r3['posterior_probability']} source={r3['source']}")
    ok &= r3["sos_triggered"] is False

    print("\nSMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
