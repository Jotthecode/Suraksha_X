"""
Shared MFCC front-end for the SurakshaX voice-distress CNN.

Pure numpy implementation so that the exact same features are produced at
training time (train_voice_cnn.py) and at inference time on the server
(voice_engine.py) without torch, librosa or numba.

Parameters (paper Section IV-C):
  - 16 kHz mono input, fixed 1.0 s window (16000 samples)
  - 25 ms Hamming window (n_fft = 400), 10 ms hop (160) -> 101 frames
  - 64-band mel filterbank (HTK mel scale, 20 Hz - 8 kHz), log compression
  - DCT-II (orthonormal) -> 40 cepstral coefficients
  - per-utterance mean/variance normalization (per-coefficient mean removal,
    one utterance-level standard deviation)
Output shape: (40, 101), float32.
"""

import numpy as np

SAMPLE_RATE = 16000
WINDOW_SECONDS = 1.0
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SECONDS)  # 16000
N_FFT = 400        # 25 ms
HOP_LENGTH = 160   # 10 ms
N_MELS = 64
N_MFCC = 40
FMIN = 20.0
FMAX = 8000.0
PRE_EMPHASIS = 0.97
DITHER = 1e-5
LOG_FLOOR = 1e-10
N_FRAMES = 1 + WINDOW_SAMPLES // HOP_LENGTH  # 101

FEATURE_PARAMS = {
    "sample_rate": SAMPLE_RATE,
    "window_seconds": WINDOW_SECONDS,
    "window_samples": WINDOW_SAMPLES,
    "n_fft": N_FFT,
    "win_length": N_FFT,
    "hop_length": HOP_LENGTH,
    "window": "hamming (symmetric, numpy.hamming)",
    "n_mels": N_MELS,
    "n_mfcc": N_MFCC,
    "fmin": FMIN,
    "fmax": FMAX,
    "mel_scale": "htk",
    "pre_emphasis": PRE_EMPHASIS,
    "dither": DITHER,
    "center": "zero-pad n_fft//2 both sides",
    "dct": "type-II orthonormal",
    "normalization": "per-utterance: subtract per-coefficient mean, divide by utterance-level std",
    "n_frames": N_FRAMES,
    "implementation": "backend/ml/features.py (numpy only)",
}


def _hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def _mel_to_hz(m):
    return 700.0 * (10.0 ** (np.asarray(m, dtype=np.float64) / 2595.0) - 1.0)


def _build_mel_filterbank():
    n_bins = N_FFT // 2 + 1
    fft_freqs = np.linspace(0.0, SAMPLE_RATE / 2.0, n_bins)
    mel_points = np.linspace(_hz_to_mel(FMIN), _hz_to_mel(FMAX), N_MELS + 2)
    hz_points = _mel_to_hz(mel_points)
    fb = np.zeros((N_MELS, n_bins), dtype=np.float64)
    for m in range(N_MELS):
        left, center, right = hz_points[m], hz_points[m + 1], hz_points[m + 2]
        up = (fft_freqs - left) / max(center - left, 1e-9)
        down = (right - fft_freqs) / max(right - center, 1e-9)
        fb[m] = np.maximum(0.0, np.minimum(up, down))
    # Slaney-style area normalisation
    enorm = 2.0 / (hz_points[2:N_MELS + 2] - hz_points[:N_MELS])
    fb *= enorm[:, None]
    return fb


def _build_dct_matrix():
    # Orthonormal DCT-II, rows = cepstral index k, cols = mel band n
    n = np.arange(N_MELS)
    k = np.arange(N_MFCC)[:, None]
    mat = np.cos(np.pi / N_MELS * (n + 0.5) * k)
    mat *= np.sqrt(2.0 / N_MELS)
    mat[0] *= 1.0 / np.sqrt(2.0)
    return mat


_WINDOW = np.hamming(N_FFT)
_MEL_FB = _build_mel_filterbank()
_DCT = _build_dct_matrix()
_DITHER_NOISE = np.random.default_rng(1234).standard_normal(WINDOW_SAMPLES) * DITHER


def fix_length(audio: np.ndarray, length: int = WINDOW_SAMPLES) -> np.ndarray:
    """Center-pad with zeros or center-crop to exactly `length` samples."""
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    n = audio.shape[0]
    if n == length:
        return audio
    if n > length:
        start = (n - length) // 2
        return audio[start:start + length]
    pad_left = (length - n) // 2
    return np.pad(audio, (pad_left, length - n - pad_left))


def mfcc(audio: np.ndarray) -> np.ndarray:
    """
    Compute the normalized 40 x 101 MFCC matrix of a 1.0 s, 16 kHz mono clip.
    Input is padded/cropped to exactly 16000 samples. Deterministic.
    """
    x = fix_length(audio).astype(np.float64)
    x = x + _DITHER_NOISE
    x = np.append(x[0], x[1:] - PRE_EMPHASIS * x[:-1])
    pad = N_FFT // 2
    x = np.pad(x, (pad, pad))
    n_frames = 1 + (x.shape[0] - N_FFT) // HOP_LENGTH  # 101
    idx = np.arange(N_FFT)[None, :] + HOP_LENGTH * np.arange(n_frames)[:, None]
    frames = x[idx] * _WINDOW[None, :]
    power = np.abs(np.fft.rfft(frames, n=N_FFT, axis=1)) ** 2  # (101, 201)
    mel = power @ _MEL_FB.T  # (101, 64)
    log_mel = np.log(np.maximum(mel, LOG_FLOOR))
    ceps = log_mel @ _DCT.T  # (101, 40)
    ceps = ceps.T  # (40, 101)
    mean = ceps.mean(axis=1, keepdims=True)
    ceps = ceps - mean
    # single utterance-level std (keeps the natural decay of higher cepstra instead of
    # blowing them up to unit variance, which made training much harder)
    ceps = ceps / (ceps.std() + 1e-5)
    return ceps.astype(np.float32)


def mfcc_batch(windows) -> np.ndarray:
    """Stack MFCCs of several 1 s windows into an [N, 1, 40, 101] float32 array."""
    feats = [mfcc(w) for w in windows]
    if not feats:
        return np.zeros((0, 1, N_MFCC, N_FRAMES), dtype=np.float32)
    return np.stack(feats)[:, None, :, :].astype(np.float32)


def sliding_windows(audio: np.ndarray, hop_seconds: float = 0.25):
    """Split a clip into 1.0 s windows with the given hop (short clips are padded)."""
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    if audio.shape[0] <= WINDOW_SAMPLES:
        return [fix_length(audio)]
    hop = int(hop_seconds * SAMPLE_RATE)
    starts = list(range(0, audio.shape[0] - WINDOW_SAMPLES + 1, hop))
    last = audio.shape[0] - WINDOW_SAMPLES
    if starts[-1] != last:
        starts.append(last)
    return [audio[s:s + WINDOW_SAMPLES] for s in starts]
