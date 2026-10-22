"""
Audio decoding helpers (no torch / librosa / system ffmpeg needed).

decode_audio(path_or_filelike) -> float32 mono numpy array at 16 kHz.
Uses PyAV (bundles ffmpeg) for wav, m4a/mp4 AAC, 3gp/amr, webm/ogg opus, mp3, ...
Falls back to the stdlib `wave` module for PCM wav files if PyAV is unavailable.
"""

import io
import wave

import numpy as np

TARGET_SR = 16000


def _decode_with_av(source, target_sr=TARGET_SR):
    import av  # PyAV

    chunks = []
    with av.open(source) as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise ValueError("no audio stream found")
        resampler = av.AudioResampler(format="flt", layout="mono", rate=target_sr)
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)


def _resample_linear(x, sr, target_sr):
    if sr == target_sr or x.size == 0:
        return x.astype(np.float32)
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(sr), int(target_sr))
        return resample_poly(x, target_sr // g, sr // g).astype(np.float32)
    except Exception:
        n_out = int(round(x.size * target_sr / sr))
        return np.interp(np.linspace(0, x.size - 1, n_out), np.arange(x.size), x).astype(np.float32)


def _decode_wav_stdlib(source, target_sr=TARGET_SR):
    with wave.open(source, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported wav sample width {width}")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return _resample_linear(x, sr, target_sr)


def decode_audio(path: str, target_sr: int = TARGET_SR) -> np.ndarray:
    """Decode an audio file of (almost) any container/codec to 16 kHz mono float32."""
    err = None
    try:
        return _decode_with_av(path, target_sr)
    except Exception as e:  # pragma: no cover - fallback path
        err = e
    try:
        return _decode_wav_stdlib(path, target_sr)
    except Exception:
        raise RuntimeError(f"could not decode audio '{path}': {err}")


def decode_audio_bytes(data: bytes, target_sr: int = TARGET_SR) -> np.ndarray:
    err = None
    try:
        return _decode_with_av(io.BytesIO(data), target_sr)
    except Exception as e:
        err = e
    try:
        return _decode_wav_stdlib(io.BytesIO(data), target_sr)
    except Exception:
        raise RuntimeError(f"could not decode audio bytes: {err}")


def write_wav(path: str, audio: np.ndarray, sr: int = TARGET_SR):
    """Write 16-bit PCM mono wav with the stdlib (no soundfile needed)."""
    x = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    pcm = (x * 32767.0).astype("<i2")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def encode_with_av(audio: np.ndarray, fmt: str = "mp4", codec: str = "aac",
                   sr: int = TARGET_SR, bit_rate: int = 32000) -> bytes:
    """Encode mono float audio into an in-memory container (e.g. AAC in mp4/m4a)."""
    import av

    buf = io.BytesIO()
    x = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    with av.open(buf, mode="w", format=fmt) as container:
        stream = container.add_stream(codec, rate=sr)
        stream.layout = "mono"
        if bit_rate:
            stream.bit_rate = bit_rate
        frame_size = stream.codec_context.frame_size or 1024
        pts = 0
        for start in range(0, x.size, frame_size):
            chunk = x[start:start + frame_size]
            frame = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format="flt", layout="mono")
            frame.sample_rate = sr
            frame.pts = pts
            pts += chunk.size
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return buf.getvalue()
