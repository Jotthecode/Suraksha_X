"""
CNN Voice-Activated SOS Recognition Module
Based on: 'AI-Based Women Safety App' (IJRASET May 2026)
Authors: Pranav Darekar, Swaraj Dorage, Prathmeah Gaikwad, Harish Senthil, Prof. Geetanjali Bansod

Implements (Section IV-C):
- 4-layer CNN (2x Conv2D + BatchNorm + ReLU + MaxPool, 2x FC, Softmax) trained in
  backend/ml/train_voice_cnn.py and shipped as ONNX (backend/models/voice_cnn.onnx)
- 40-dimensional MFCCs (25 ms Hamming window, 10 ms frame shift, 1.0 s window),
  computed with numpy only (backend/ml/features.py) - identical to training
- Multi-lingual distress keywords: HELP, SAVE ME, EMERGENCY (English), BACHAO,
  MADAD KARO (Hindi), MADAT KARA, VACHVA (Marathi), KAPAATHU (Tamil), SAHAJJO KORO (Bengali)
- Posterior probability >= 0.85 triggers hands-free SOS
- Sliding 1.0 s window / 0.25 s hop over arbitrary-length recordings

Runtime dependencies: numpy, onnxruntime, av (PyAV). No torch / librosa at inference.
If the model or onnxruntime is unavailable, classify_audio_* returns
{"source": "unavailable", "sos_triggered": False, ...} instead of raising.

The text path (classify_audio_phrase) is kept as a transcript-keyword fallback
("source": "keyword_text"); its probabilities are heuristic, not model outputs.

NOTE: the shipped CNN is trained on synthetic multilingual TTS speech + augmentation
(see backend/ml/README.md). Add real recordings to improve real-world accuracy.
"""

import datetime
import json
import os
import sys
import tempfile
import threading
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ml.features import (FEATURE_PARAMS, SAMPLE_RATE, mfcc_batch,  # noqa: E402
                         sliding_windows)

MODEL_PATH = os.path.join(_HERE, "models", "voice_cnn.onnx")
LABELS_PATH = os.path.join(_HERE, "models", "voice_cnn_labels.json")

WINDOW = SAMPLE_RATE  # 1 s model input


def speech_segments(x, top_db=35.0, frame=400, hop=160, min_gap=0.25, min_len=0.12):
    """
    Energy-based voice activity split that mirrors the librosa.effects.trim(top_db=35)
    used when the training clips were built. Returns [(start, end)] sample ranges.
    """
    if x.size < frame:
        return [(0, x.size)]
    nfr = 1 + (x.size - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(nfr)[:, None]
    db = 20 * np.log10(np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12))
    active = db > db.max() - top_db
    segs, start = [], None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            segs.append([start, i])
            start = None
    if start is not None:
        segs.append([start, nfr])
    merged = []
    for seg in segs:  # join short pauses, e.g. "help ... help"
        if merged and (seg[0] - merged[-1][1]) * hop / SAMPLE_RATE < min_gap:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    out = [(a * hop, min(x.size, b * hop + frame)) for a, b in merged]
    return [(a, b) for a, b in out if (b - a) / SAMPLE_RATE >= min_len] or [(0, x.size)]


def segment_windows(x, hop_seconds=0.25):
    """
    Build 1 s model inputs the same way training clips were made (ml/augment.fit_to_window):
    each speech segment is peak-normalised; short ones are centred, ones up to 1.3 s are
    time-compressed into 1 s, longer ones contribute their last second plus sliding windows.
    Returns (windows, start_seconds).
    """
    from scipy.signal import resample

    wins, starts = [], []
    for a, b in speech_segments(x):
        seg = x[a:b]
        seg = seg / (np.max(np.abs(seg)) + 1e-9) * 0.8
        t0 = a / SAMPLE_RATE
        if seg.size <= WINDOW:
            pad = WINDOW - seg.size
            wins.append(np.pad(seg, (pad // 2, pad - pad // 2)))
            starts.append(t0)
            continue
        if seg.size / WINDOW <= 1.3:
            wins.append(resample(seg, WINDOW).astype(np.float32))
            starts.append(t0)
        wins.append(seg[-WINDOW:])
        starts.append((b - WINDOW) / SAMPLE_RATE)
        for i, w in enumerate(sliding_windows(seg, hop_seconds)):
            wins.append(w)
            starts.append(t0 + i * hop_seconds)
    return wins, starts


MODEL_ARCHITECTURE = "4-Layer CNN (2x Conv2D + BatchNorm + MaxPool, 2x FC, Softmax)"
MFCC_DIMENSION = "40-dim (25ms Hamming window, 10ms frame shift)"

# Canonical distress keyword lexicon supported in the paper (used by the text fallback)
DISTRESS_KEYWORDS = {
    # English
    "help": {"language": "English", "keyword": "HELP", "base_confidence": 0.96},
    "save me": {"language": "English", "keyword": "SAVE ME", "base_confidence": 0.94},
    "emergency": {"language": "English", "keyword": "EMERGENCY", "base_confidence": 0.92},
    # Hindi
    "bachao": {"language": "Hindi", "keyword": "BACHAO", "base_confidence": 0.97},
    "madad": {"language": "Hindi", "keyword": "MADAD", "base_confidence": 0.93},
    "madad karo": {"language": "Hindi", "keyword": "MADAD KARO", "base_confidence": 0.95},
    # Marathi (Local Pune regional language)
    "madat kara": {"language": "Marathi", "keyword": "MADAT KARA", "base_confidence": 0.95},
    "vachva": {"language": "Marathi", "keyword": "VACHVA", "base_confidence": 0.94},
    # Tamil
    "kapaathu": {"language": "Tamil", "keyword": "KAPAATHU", "base_confidence": 0.91},
    # Bengali
    "sahajjo": {"language": "Bengali", "keyword": "SAHAJJO", "base_confidence": 0.92},
    "sahajjo koro": {"language": "Bengali", "keyword": "SAHAJJO KORO", "base_confidence": 0.93},
}

# Ambient noise conditions from Table 3 of the paper
NOISE_PROFILES = {
    "quiet": {"snr_db": 35, "accuracy": 0.972, "label": "Quiet Environment (> 30 dB)"},
    "office": {"snr_db": 25, "accuracy": 0.941, "label": "Office Background (20-30 dB)"},
    "street": {"snr_db": 15, "accuracy": 0.928, "label": "Street / Traffic Noise (10-20 dB)"},
    "crowd": {"snr_db": 8, "accuracy": 0.873, "label": "Crowd / Market Noise (5-10 dB)"},
    "extreme": {"snr_db": 3, "accuracy": 0.796, "label": "Extreme Noise (< 5 dB)"},
}

_DEFAULT_DISPLAY = {
    "help": ("HELP", "English"), "save_me": ("SAVE ME", "English"), "emergency": ("EMERGENCY", "English"),
    "bachao": ("BACHAO", "Hindi"), "madad_karo": ("MADAD KARO", "Hindi"),
    "madat_kara": ("MADAT KARA", "Marathi"), "vachva": ("VACHVA", "Marathi"),
    "kapaathu": ("KAPAATHU", "Tamil"), "sahajjo_koro": ("SAHAJJO KORO", "Bengali"),
    "background": ("NONE (Safe / Ambient)", "None"),
}
SAFE_KEYWORD = "NONE (Safe / Ambient)"


def _noise_key_from_snr(snr_db: float) -> str:
    if snr_db > 30:
        return "quiet"
    if snr_db > 20:
        return "office"
    if snr_db > 10:
        return "street"
    if snr_db > 5:
        return "crowd"
    return "extreme"


def _estimate_snr_and_level(audio: np.ndarray):
    """
    Rough SNR estimate from frame-energy percentiles (20 ms frames):
    noise floor = 10th percentile energy, speech = 95th percentile energy.
    Also returns a 0..1 loudness level (loudest-frame RMS mapped from -60..0 dBFS).
    """
    frame = int(0.02 * SAMPLE_RATE)
    n = audio.size // frame
    if n < 2:
        r = float(np.sqrt(np.mean(audio ** 2) + 1e-12))
        return 35.0, float(np.clip((20 * np.log10(r + 1e-12) + 60) / 60, 0, 1))
    e = np.mean(audio[: n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12
    noise = np.percentile(e, 10)
    speech = np.percentile(e, 95)
    snr = float(np.clip(10 * np.log10(speech / noise), -5.0, 60.0))
    peak_rms = float(np.sqrt(speech))
    level = float(np.clip((20 * np.log10(peak_rms + 1e-12) + 60) / 60, 0.0, 1.0))
    return snr, level


class CNNVoiceSOSClassifier:
    def __init__(self, model_path: str = MODEL_PATH, labels_path: str = LABELS_PATH):
        self.threshold = 0.85  # Decision threshold specified in Section IV-C
        self.mfcc_dim = 40     # 40-dimensional MFCCs (25ms window, 10ms hop)
        self.hop_seconds = 0.25
        self.model_path = model_path
        self.labels_path = labels_path
        self._session = None
        self._load_error = None
        self._lock = threading.Lock()
        self.classes = list(_DEFAULT_DISPLAY.keys())
        self.display = {c: {"keyword": k, "language": l} for c, (k, l) in _DEFAULT_DISPLAY.items()}
        self.background_class = "background"

    # ------------------------------------------------------------ model loading
    def _ensure_session(self):
        if self._session is not None:
            return True
        if self._load_error is not None:
            return False
        with self._lock:
            if self._session is not None:
                return True
            try:
                import onnxruntime as ort
                if not os.path.exists(self.model_path):
                    raise FileNotFoundError(f"model file not found: {self.model_path}")
                if os.path.exists(self.labels_path):
                    with open(self.labels_path, encoding="utf-8") as f:
                        labels = json.load(f)
                    self.classes = labels["classes"]
                    self.display = labels.get("display", self.display)
                    self.threshold = float(labels.get("threshold", self.threshold))
                    self.background_class = labels.get("background_class", "background")
                    self.hop_seconds = float(labels.get("inference", {}).get("hop_seconds", self.hop_seconds))
                so = ort.SessionOptions()
                so.intra_op_num_threads = 1
                so.inter_op_num_threads = 1
                self._session = ort.InferenceSession(self.model_path, so, providers=["CPUExecutionProvider"])
                return True
            except Exception as e:  # missing model / onnxruntime import failure
                self._load_error = f"{type(e).__name__}: {e}"
                return False

    @property
    def model_available(self) -> bool:
        return self._ensure_session()

    # ------------------------------------------------------------ text fallback
    def classify_audio_phrase(self, text_or_transcript: str = "", audio_score: float = 0.0, noise_env: str = "street"):
        """
        Transcript keyword fallback (no audio available). Heuristic probabilities:
        base keyword confidence scaled by the paper's Table-3 noise accuracy.
        Returns the same keys as classify_audio_file with "source": "keyword_text".
        """
        t_start = time.perf_counter()

        normalized_phrase = (text_or_transcript or "").lower().strip()
        matched_entry = None
        # longest keys first so "madad karo" wins over "madad"
        for key in sorted(DISTRESS_KEYWORDS, key=len, reverse=True):
            if key in normalized_phrase:
                matched_entry = DISTRESS_KEYWORDS[key]
                break

        noise_info = NOISE_PROFILES.get((noise_env or "street").lower(), NOISE_PROFILES["street"])
        noise_factor = noise_info["accuracy"]
        try:
            audio_score = float(audio_score or 0.0)
        except (TypeError, ValueError):
            audio_score = 0.0

        if matched_entry is not None:
            posterior_prob = matched_entry["base_confidence"] * (noise_factor / 0.972)
            posterior_prob = float(np.clip(posterior_prob, 0.10, 0.99))
            detected_keyword = matched_entry["keyword"]
            language = matched_entry["language"]
        elif audio_score > 0.70:
            # High acoustic energy (scream) without a recognised transcript
            posterior_prob = float(np.clip(audio_score * 0.95, 0.70, 0.98))
            detected_keyword = "ACOUSTIC_SCREAM_DISTRESS"
            language = "Acoustic Vocalization"
        else:
            posterior_prob = float(np.clip(audio_score * 0.40, 0.02, 0.45))
            detected_keyword = SAFE_KEYWORD
            language = "None"

        is_triggered = posterior_prob >= self.threshold
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "sos_triggered": bool(is_triggered),
            "posterior_probability": round(posterior_prob, 4),
            "threshold": self.threshold,
            "detected_keyword": detected_keyword,
            "language": language,
            "noise_condition": noise_info["label"],
            "snr_db": noise_info["snr_db"],
            "inference_latency_ms": round(elapsed_ms, 3),
            "model_architecture": MODEL_ARCHITECTURE,
            "mfcc_dimension": MFCC_DIMENSION,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "source": "keyword_text",
        }

    # ------------------------------------------------------------ audio path
    def _unavailable(self, reason: str, t_start: float, duration: float = 0.0):
        return {
            "sos_triggered": False,
            "posterior_probability": 0.0,
            "threshold": self.threshold,
            "detected_keyword": SAFE_KEYWORD,
            "language": "None",
            "noise_condition": None,
            "snr_db": None,
            "inference_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
            "model_architecture": MODEL_ARCHITECTURE,
            "mfcc_dimension": MFCC_DIMENSION,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "source": "unavailable",
            "error": reason,
            "class_probabilities": {},
            "windows_evaluated": 0,
            "audio_duration_s": round(duration, 3),
            "rms_level": 0.0,
        }

    def classify_audio_array(self, audio: np.ndarray, sample_rate: int = SAMPLE_RATE, _t_start: float = None) -> dict:
        """Classify a mono float waveform (resampled to 16 kHz if needed)."""
        t_start = _t_start if _t_start is not None else time.perf_counter()
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if sample_rate != SAMPLE_RATE and audio.size:
            from ml.audio_io import _resample_linear
            audio = _resample_linear(audio, sample_rate, SAMPLE_RATE)
        duration = audio.size / SAMPLE_RATE
        if not self._ensure_session():
            return self._unavailable(f"voice CNN unavailable ({self._load_error})", t_start, duration)
        if audio.size < int(0.1 * SAMPLE_RATE):
            return self._unavailable("audio too short (< 0.1 s)", t_start, duration) | {"source": "cnn_audio"}

        audio = audio - float(np.mean(audio))
        snr_db, level = _estimate_snr_and_level(audio)
        noise_key = _noise_key_from_snr(snr_db)

        windows, starts = segment_windows(audio, self.hop_seconds)
        feats = mfcc_batch(windows)
        logits = self._session.run(["logits"], {"mfcc": feats})[0].astype(np.float64)
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)

        bg = self.classes.index(self.background_class)
        kw_probs = probs.copy()
        kw_probs[:, bg] = -1.0
        best_win = int(np.argmax(kw_probs.max(axis=1)))
        best_cls = int(np.argmax(kw_probs[best_win]))
        posterior = float(probs[best_win, best_cls])
        triggered = posterior >= self.threshold

        if triggered:
            cls_name = self.classes[best_cls]
        else:
            cls_name = self.background_class
        disp = self.display.get(cls_name, {"keyword": cls_name.upper(), "language": "Unknown"})
        win_probs = probs[best_win]

        return {
            "sos_triggered": bool(triggered),
            "posterior_probability": round(posterior, 4),
            "threshold": self.threshold,
            "detected_keyword": disp["keyword"] if triggered else SAFE_KEYWORD,
            "language": disp["language"] if triggered else "None",
            "noise_condition": NOISE_PROFILES[noise_key]["label"],
            "snr_db": round(snr_db, 1),
            "inference_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
            "model_architecture": MODEL_ARCHITECTURE,
            "mfcc_dimension": MFCC_DIMENSION,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "source": "cnn_audio",
            "class_probabilities": {c: round(float(p), 4) for c, p in zip(self.classes, win_probs)},
            "top_candidate": self.classes[best_cls],
            "best_window_start_s": round(float(starts[best_win]), 2),
            "windows_evaluated": int(len(windows)),
            "audio_duration_s": round(duration, 3),
            "rms_level": round(level, 3),
        }

    def classify_audio_file(self, path: str) -> dict:
        """Decode any wav / m4a(AAC) / 3gp(AMR) / webm|ogg(Opus) / mp3 file and classify it."""
        t_start = time.perf_counter()
        if not self._ensure_session():
            return self._unavailable(f"voice CNN unavailable ({self._load_error})", t_start)
        try:
            from ml.audio_io import decode_audio
            audio = decode_audio(path)
        except Exception as e:
            return self._unavailable(f"audio decode failed: {e}", t_start) | {"source": "cnn_audio"}
        return self.classify_audio_array(audio, SAMPLE_RATE, _t_start=t_start)

    def classify_audio_bytes(self, data: bytes, suffix: str = ".m4a") -> dict:
        """Classify an uploaded audio payload (bytes). `suffix` hints the container format."""
        t_start = time.perf_counter()
        if not self._ensure_session():
            return self._unavailable(f"voice CNN unavailable ({self._load_error})", t_start)
        try:
            from ml.audio_io import decode_audio_bytes, decode_audio
            try:
                audio = decode_audio_bytes(data)
            except Exception:
                # some containers (e.g. 3gp/mp4 with moov at end) decode more reliably from a real file
                fd, tmp = tempfile.mkstemp(suffix=suffix or ".bin")
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(data)
                    audio = decode_audio(tmp)
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
        except Exception as e:
            return self._unavailable(f"audio decode failed: {e}", t_start) | {"source": "cnn_audio"}
        return self.classify_audio_array(audio, SAMPLE_RATE, _t_start=t_start)

    def model_info(self) -> dict:
        ok = self._ensure_session()
        return {"available": ok, "error": self._load_error, "model_path": self.model_path,
                "classes": self.classes, "threshold": self.threshold, "feature_params": FEATURE_PARAMS}


# Singleton instance
_voice_classifier_instance = None


def get_voice_classifier():
    global _voice_classifier_instance
    if _voice_classifier_instance is None:
        _voice_classifier_instance = CNNVoiceSOSClassifier()
    return _voice_classifier_instance


def classify_audio_file(path: str) -> dict:
    return get_voice_classifier().classify_audio_file(path)


def classify_audio_bytes(data: bytes, suffix: str = ".m4a") -> dict:
    return get_voice_classifier().classify_audio_bytes(data, suffix)
