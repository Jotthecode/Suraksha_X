"""
Audio augmentation used to build the training set (training-time only; uses
librosa + scipy, which are NOT needed on the inference server).
"""

import numpy as np
from scipy import signal

from .features import SAMPLE_RATE as SR, WINDOW_SAMPLES


# ----------------------------------------------------------------- noises
def white_noise(n, rng):
    return rng.standard_normal(n).astype(np.float32)


def _colored(n, rng, exponent):
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n)
    f[0] = f[1]
    spec /= f ** (exponent / 2.0)
    x = np.fft.irfft(spec, n=n)
    return (x / (np.std(x) + 1e-9)).astype(np.float32)


def pink_noise(n, rng):
    return _colored(n, rng, 1.0)


def brown_noise(n, rng):
    return _colored(n, rng, 2.0)


def traffic_noise(n, rng):
    """Synthetic traffic hum: low-passed brown noise + engine harmonics + slow swells."""
    t = np.arange(n) / SR
    base = brown_noise(n, rng)
    f0 = rng.uniform(40, 110)
    hum = sum((0.6 / k) * np.sin(2 * np.pi * f0 * k * t + rng.uniform(0, 6.28)) for k in range(1, 6))
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(0.1, 0.5) * t + rng.uniform(0, 6.28))
    hiss = signal.lfilter(*signal.butter(2, rng.uniform(1500, 4000) / (SR / 2), "low"), white_noise(n, rng))
    x = (base + 0.5 * hum + 0.3 * hiss) * swell
    if rng.random() < 0.3:  # passing horn
        s = rng.integers(0, max(1, n - SR // 2))
        L = min(n - s, int(SR * rng.uniform(0.2, 0.5)))
        fh = rng.uniform(300, 600)
        x[s:s + L] += 2.0 * np.sign(np.sin(2 * np.pi * fh * np.arange(L) / SR))
    return (x / (np.std(x) + 1e-9)).astype(np.float32)


def babble_noise(n, rng, speech_pool, k=None):
    """Mix several speech clips (background phrases) to form crowd babble."""
    if not speech_pool:
        return pink_noise(n, rng)
    k = k or int(rng.integers(3, 7))
    out = np.zeros(n, dtype=np.float32)
    for _ in range(k):
        clip = speech_pool[int(rng.integers(0, len(speech_pool)))]
        if clip.size < n:
            clip = np.tile(clip, int(np.ceil(n / max(clip.size, 1))) + 1)
        s = int(rng.integers(0, clip.size - n + 1))
        seg = clip[s:s + n]
        out += seg / (np.std(seg) + 1e-6) * rng.uniform(0.5, 1.0)
    return (out / (np.std(out) + 1e-9)).astype(np.float32)


def random_noise(n, rng, speech_pool):
    kind = rng.choice(["white", "pink", "brown", "traffic", "babble", "babble"])
    if kind == "white":
        return white_noise(n, rng), kind
    if kind == "pink":
        return pink_noise(n, rng), kind
    if kind == "brown":
        return brown_noise(n, rng), kind
    if kind == "traffic":
        return traffic_noise(n, rng), kind
    return babble_noise(n, rng, speech_pool), kind


# ----------------------------------------------------------------- effects
def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def add_noise(x, noise, snr_db):
    sig = rms(x[np.abs(x) > 1e-4]) if np.any(np.abs(x) > 1e-4) else rms(x)
    noise = noise[: x.size]
    scale = sig / (rms(noise) * (10 ** (snr_db / 20.0)) + 1e-12)
    return (x + noise * scale).astype(np.float32)


def reverb(x, rng):
    rt60 = rng.uniform(0.15, 0.7)
    L = int(SR * rt60)
    t = np.arange(L) / SR
    ir = rng.standard_normal(L) * np.exp(-6.9 * t / rt60)
    ir[0] = 1.0
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = signal.fftconvolve(x, ir)[: x.size]
    mix = rng.uniform(0.2, 0.6)
    y = (1 - mix) * x + mix * wet
    return (y * rms(x) / (rms(y) + 1e-9)).astype(np.float32)


def lowpass(x, cutoff):
    b, a = signal.butter(4, min(cutoff, SR / 2 - 100) / (SR / 2), "low")
    return signal.lfilter(b, a, x).astype(np.float32)


def phone_band(x, rng):
    """Telephone / cheap phone-mic: band-pass ~300-3400 Hz via 8 kHz round trip."""
    lo = rng.uniform(150, 400)
    b, a = signal.butter(2, [lo / (SR / 2), 3400 / (SR / 2)], "band")
    y = signal.lfilter(b, a, x)
    y = signal.resample_poly(signal.resample_poly(y, 1, 2), 2, 1)[: x.size]
    return y.astype(np.float32)


def aac_like(x, rng):
    """Real AAC round trip through PyAV when available, otherwise bandlimit+quantise."""
    try:
        from .audio_io import encode_with_av, decode_audio_bytes
        br = int(rng.choice([24000, 32000, 48000, 64000]))
        y = decode_audio_bytes(encode_with_av(x, "mp4", "aac", bit_rate=br))
        # any residual encoder delay (<= ~64 ms) just acts as an extra time shift
        y = np.pad(y[: x.size], (0, max(0, x.size - y.size)))
        return y.astype(np.float32)
    except Exception:
        y = lowpass(x, rng.uniform(5000, 7500))
        q = 2 ** int(rng.integers(8, 12))
        return (np.round(y * q) / q).astype(np.float32)


def shout(x, rng):
    """Approximate shouting: pitch up a bit, compress and saturate."""
    import librosa
    y = librosa.effects.pitch_shift(x, sr=SR, n_steps=float(rng.uniform(1.0, 3.0)))
    drive = rng.uniform(2.0, 6.0)
    y = np.tanh(drive * y / (np.max(np.abs(y)) + 1e-9)) / np.tanh(drive)
    return y.astype(np.float32)


def speed_pitch(x, rng):
    import librosa
    y = x
    if rng.random() < 0.6:
        y = librosa.effects.time_stretch(y, rate=float(rng.uniform(0.85, 1.18)))
    if rng.random() < 0.6:
        y = librosa.effects.pitch_shift(y, sr=SR, n_steps=float(rng.uniform(-2.5, 2.5)))
    return y.astype(np.float32)


def trim(x, top_db=35):
    import librosa
    if x.size == 0:
        return x
    y, _ = librosa.effects.trim(x, top_db=top_db, frame_length=512, hop_length=128)
    return y if y.size > 0 else x


def fit_to_window(x, rng, length=WINDOW_SAMPLES, keyword=True):
    """
    Place an utterance in a fixed 1 s window at a random offset.
    Long keyword utterances are time-compressed (<=1.3x) or the LAST second is
    kept (keywords sit at the end of carrier phrases like "mujhe bachao").
    Long background utterances get a random 1 s crop.
    """
    import librosa
    if x.size > length:
        ratio = x.size / length
        if keyword and ratio <= 1.3:
            x = librosa.effects.time_stretch(x, rate=ratio * 1.02)[:length]
        elif keyword:
            x = x[-length:]
        else:
            s = int(rng.integers(0, x.size - length + 1))
            x = x[s:s + length]
    out = np.zeros(length, dtype=np.float32)
    off = int(rng.integers(0, length - x.size + 1))
    out[off:off + x.size] = x[:length]
    return out


def augment_clip(speech, rng, speech_pool, keyword=True, strength=1.0):
    """Full augmentation chain for one utterance -> 1 s, 16 kHz float32 window."""
    x = speech.astype(np.float32)
    if rng.random() < 0.5 * strength:
        x = speed_pitch(x, rng)
    if keyword and rng.random() < 0.2 * strength:
        x = shout(x, rng)
    x = fit_to_window(x, rng, keyword=keyword)
    if rng.random() < 0.3 * strength:
        x = reverb(x, rng)
    if rng.random() < 0.85:
        noise, _ = random_noise(x.size, rng, speech_pool)
        snr = float(rng.uniform(0, 30)) if rng.random() < 0.3 else float(rng.uniform(8, 30))
        x = add_noise(x, noise, snr)
    else:
        x = x + white_noise(x.size, rng) * 10 ** (rng.uniform(-80, -55) / 20)
    r = rng.random()
    if r < 0.2 * strength:
        x = lowpass(x, rng.uniform(2800, 7000))
    elif r < 0.35 * strength:
        x = phone_band(x, rng)
    elif r < 0.5 * strength:
        x = aac_like(x, rng)
    peak = np.max(np.abs(x)) + 1e-9
    target_peak = 10 ** (rng.uniform(-24, -1) / 20.0)
    return (x / peak * target_peak).astype(np.float32)
