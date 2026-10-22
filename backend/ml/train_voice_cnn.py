"""
Train the SurakshaX voice-distress keyword CNN (paper Section IV-C) and export to ONNX.

Inputs : backend/ml/data/voice/<class>/*.wav + metadata.csv  (generate_voice_dataset.py)
         backend/ml/data/voice_real/<class>/*.{wav,m4a,mp3,3gp,webm,ogg,...}  (optional, real recordings)
Outputs: backend/models/voice_cnn.onnx, backend/models/voice_cnn_labels.json,
         backend/models/voice_cnn.pt (torch weights),
         backend/ml/reports/voice_cnn_metrics.json, backend/ml/reports/voice_cnn_report.md

Usage:  python backend/ml/train_voice_cnn.py [--epochs 40] [--real-weight 3.0]
"""

import argparse
import csv
import datetime
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,  # noqa: E402
                             precision_recall_fscore_support)
from sklearn.model_selection import train_test_split  # noqa: E402

from ml.features import FEATURE_PARAMS, N_FRAMES, N_MFCC, mfcc  # noqa: E402
from ml.audio_io import decode_audio, _decode_wav_stdlib  # noqa: E402
from ml.generate_voice_dataset import CLASSES, HELDOUT_VOICES  # noqa: E402

DATA_DIR = os.path.join(HERE, "data", "voice")
REAL_DIR = os.path.join(HERE, "data", "voice_real")
REPORT_DIR = os.path.join(HERE, "reports")
MODEL_DIR = os.path.join(BACKEND, "models")
THRESHOLD = 0.85
BG = CLASSES.index("background")

DISPLAY = {
    "help": ("HELP", "English"), "save_me": ("SAVE ME", "English"), "emergency": ("EMERGENCY", "English"),
    "bachao": ("BACHAO", "Hindi"), "madad_karo": ("MADAD KARO", "Hindi"),
    "madat_kara": ("MADAT KARA", "Marathi"), "vachva": ("VACHVA", "Marathi"),
    "kapaathu": ("KAPAATHU", "Tamil"), "sahajjo_koro": ("SAHAJJO KORO", "Bengali"),
    "background": ("NONE (Safe / Ambient)", "None"),
}
ARCH = "4-Layer CNN (2x Conv2D + BatchNorm + ReLU + MaxPool, 2x FC, Softmax)"


class VoiceCNN(nn.Module):
    """2x [Conv2D + BN + ReLU + MaxPool] -> FC -> FC (softmax applied at inference)."""

    def __init__(self, n_classes=len(CLASSES), c1=32, c2=64, hidden=128):
        super().__init__()
        self.conv1 = nn.Conv2d(1, c1, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(c1)
        self.pool1 = nn.MaxPool2d(2)              # 40x101 -> 20x50
        self.conv2 = nn.Conv2d(c1, c2, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(c2)
        self.pool2 = nn.MaxPool2d((2, 5))         # 20x50 -> 10x10 (coarser time pooling = shift tolerance)
        self.drop1 = nn.Dropout(0.2)
        self.fc1 = nn.Linear(c2 * (N_MFCC // 4) * ((N_FRAMES // 2) // 5), hidden)
        self.drop2 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(hidden, n_classes)

    def forward(self, x):
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = self.drop1(torch.flatten(x, 1))
        x = self.drop2(F.relu(self.fc1(x)))
        return self.fc2(x)


def spec_augment(x, rng, p=0.6, n_freq=1, max_f=6, n_time=2, max_t=10):
    """SpecAugment on a batch tensor [B,1,40,101] (masked to 0 = utterance mean after CMVN)."""
    x = x.clone()
    B = x.shape[0]
    for b in range(B):
        if rng.random() > p:
            continue
        for _ in range(n_freq):
            w = int(rng.integers(0, max_f + 1))
            f0 = int(rng.integers(0, N_MFCC - w + 1))
            x[b, :, f0:f0 + w, :] = 0
        for _ in range(n_time):
            w = int(rng.integers(0, max_t + 1))
            t0 = int(rng.integers(0, N_FRAMES - w + 1))
            x[b, :, :, t0:t0 + w] = 0
    return x


# ------------------------------------------------------------------ data
def load_synthetic():
    meta_path = os.path.join(DATA_DIR, "metadata.csv")
    if not os.path.exists(meta_path):
        sys.exit("metadata.csv missing - run generate_voice_dataset.py first")
    rows = list(csv.DictReader(open(meta_path, encoding="utf-8")))
    cache = os.path.join(DATA_DIR, "mfcc_cache.npz")
    stamp = f"{os.path.getmtime(meta_path)}|{len(rows)}|{json.dumps(FEATURE_PARAMS, sort_keys=True)}"
    if os.path.exists(cache):
        c = np.load(cache, allow_pickle=False)
        if str(c["stamp"]) == stamp:
            print(f"loaded cached MFCCs for {len(rows)} clips")
            return rows, c["X"], np.array([CLASSES.index(r["cls"]) for r in rows])
    X = np.zeros((len(rows), 1, N_MFCC, N_FRAMES), dtype=np.float32)
    t0 = time.time()
    for i, r in enumerate(rows):
        X[i, 0] = mfcc(_decode_wav_stdlib(os.path.join(DATA_DIR, r["path"])))
    print(f"MFCC for {len(rows)} synthetic clips in {time.time() - t0:.1f}s")
    np.savez(cache, X=X, stamp=np.array(stamp))
    y = np.array([CLASSES.index(r["cls"]) for r in rows])
    return rows, X, y


def load_real(n_aug, rng):
    """Real recordings: every file -> clean window + n_aug augmented windows."""
    out_X, out_y, out_group = [], [], []
    if not os.path.isdir(REAL_DIR):
        return np.zeros((0, 1, N_MFCC, N_FRAMES), np.float32), np.zeros(0, int), []
    from ml import augment as A
    files = []
    for c in CLASSES:
        d = os.path.join(REAL_DIR, c)
        if os.path.isdir(d):
            files += [(c, os.path.join(d, f)) for f in sorted(os.listdir(d)) if not f.startswith(".")]
    for c, path in files:
        try:
            x = decode_audio(path)
        except Exception as e:
            print("  skip real clip", path, e)
            continue
        kw = c != "background"
        x = A.trim(x) if kw else x
        if x.size < 1600:
            continue
        # long background recordings -> many 1 s crops; keywords -> clean + augmented
        windows = [A.fit_to_window(x, rng, keyword=kw)]
        for _ in range(n_aug if kw else max(1, min(20, x.size // 16000))):
            windows.append(A.augment_clip(x, rng, [], keyword=kw, strength=0.7))
        for w in windows:
            out_X.append(mfcc(w)[None])
            out_y.append(CLASSES.index(c))
            out_group.append(path)
    if out_X:
        print(f"loaded {len(files)} real recordings -> {len(out_X)} windows")
    return (np.stack(out_X).astype(np.float32) if out_X else np.zeros((0, 1, N_MFCC, N_FRAMES), np.float32),
            np.array(out_y, int), out_group)


# ------------------------------------------------------------------ eval
def predict_proba(model, X, device, bs=512):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), bs):
            out.append(F.softmax(model(torch.from_numpy(X[i:i + bs]).to(device)), dim=1).cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, len(CLASSES)))


def evaluate(probs, y):
    if len(y) == 0:
        return None
    pred = probs.argmax(1)
    labels = list(range(len(CLASSES)))
    rep = classification_report(y, pred, labels=labels, target_names=CLASSES, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, pred, labels=labels)
    kw_prob = np.delete(probs, BG, axis=1).max(1)
    true_pos = y != BG
    pred_pos = kw_prob >= THRESHOLD
    p, r, f, _ = precision_recall_fscore_support(true_pos, pred_pos, average="binary", zero_division=0)
    tn = int(np.sum(~true_pos & ~pred_pos)); fp = int(np.sum(~true_pos & pred_pos))
    fn = int(np.sum(true_pos & ~pred_pos)); tp = int(np.sum(true_pos & pred_pos))
    # keyword correctly identified among triggered distress clips
    trig = true_pos & pred_pos
    kw_id_acc = float(np.mean(pred[trig] == y[trig])) if trig.any() else 0.0
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(rep["macro avg"]["f1-score"]),
        "per_class": {c: {k: float(rep[c][k]) for k in ("precision", "recall", "f1-score", "support")} for c in CLASSES},
        "confusion_matrix": cm.tolist(),
        "binary_distress_at_threshold": {
            "threshold": THRESHOLD, "precision": float(p), "recall": float(r), "f1": float(f),
            "false_positive_rate": fp / max(1, fp + tn), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "keyword_identity_accuracy_when_triggered": kw_id_acc,
        },
    }


def latency_benchmark(onnx_path, X):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    sess = ort.InferenceSession(onnx_path, so, providers=["CPUExecutionProvider"])
    audio = (np.random.default_rng(0).standard_normal(16000) * 0.05).astype(np.float32)
    x1 = X[:1]
    for _ in range(20):
        sess.run(["logits"], {"mfcc": x1})
    n = 300
    t = time.perf_counter()
    for _ in range(n):
        sess.run(["logits"], {"mfcc": x1})
    onnx_ms = (time.perf_counter() - t) / n * 1000
    t = time.perf_counter()
    for _ in range(n):
        mfcc(audio)
    mfcc_ms = (time.perf_counter() - t) / n * 1000
    # 3 s clip = 9 windows at 0.25 s hop, batched
    clip = np.random.default_rng(1).standard_normal(48000).astype(np.float32) * 0.05
    from ml.features import sliding_windows, mfcc_batch
    t = time.perf_counter()
    for _ in range(50):
        sess.run(["logits"], {"mfcc": mfcc_batch(sliding_windows(clip))})
    clip_ms = (time.perf_counter() - t) / 50 * 1000
    return {"onnx_single_window_ms": onnx_ms, "mfcc_single_window_ms": mfcc_ms,
            "end_to_end_single_window_ms": onnx_ms + mfcc_ms, "end_to_end_3s_clip_ms": clip_ms,
            "threads": 1, "runtime": f"onnxruntime {ort.__version__} CPUExecutionProvider"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=96)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--real-weight", type=float, default=3.0)
    ap.add_argument("--real-aug", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--bg-cost", type=float, default=2.0, help="extra weight on background class")
    ap.add_argument("--max-minutes", type=float, default=20.0, help="wall-clock training budget")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    print("device:", device)

    rows, X, y = load_synthetic()
    voices = np.array([r["voice"] for r in rows])
    groups = np.array([r["raw_id"] for r in rows])

    heldout_mask = np.isin(voices, HELDOUT_VOICES)
    # stratified split by raw utterance (augmented copies of one TTS clip never cross splits)
    seen_idx = np.where(~heldout_mask)[0]
    uniq, first = np.unique(groups[seen_idx], return_index=True)
    g_cls = y[seen_idx][first]
    g_train, g_tmp, c_train, c_tmp = train_test_split(uniq, g_cls, test_size=0.25, stratify=g_cls,
                                                      random_state=args.seed)
    g_val, g_test = train_test_split(g_tmp, test_size=0.5, stratify=c_tmp, random_state=args.seed)
    split = np.full(len(y), "", dtype=object)
    split[np.isin(groups, g_train) & ~heldout_mask] = "train"
    split[np.isin(groups, g_val) & ~heldout_mask] = "val"
    split[np.isin(groups, g_test) & ~heldout_mask] = "test_seen"
    split[heldout_mask] = "test_heldout"

    Xr, yr, gr = load_real(args.real_aug, rng)
    real_train_mask = np.ones(len(yr), bool)
    real_test = None
    if len(yr):
        files = np.array(sorted(set(gr)))
        if len(files) >= 10:
            test_files = rng.choice(files, size=max(1, len(files) // 5), replace=False)
            real_train_mask = ~np.isin(np.array(gr), test_files)
        real_test = (Xr[~real_train_mask], yr[~real_train_mask])

    tr = split == "train"
    X_train = np.concatenate([X[tr], Xr[real_train_mask]])
    y_train = np.concatenate([y[tr], yr[real_train_mask]])
    w_train = np.concatenate([np.ones(tr.sum()), np.full(real_train_mask.sum(), args.real_weight)]).astype(np.float32)
    X_val, y_val = X[split == "val"], y[split == "val"]
    print("split sizes:", {s: int((split == s).sum()) for s in ["train", "val", "test_seen", "test_heldout"]},
          "real train windows:", int(real_train_mask.sum()))

    counts = np.bincount(y_train, minlength=len(CLASSES)).astype(np.float32)
    cw = counts.sum() / (len(CLASSES) * np.maximum(counts, 1))
    cw[BG] *= args.bg_cost  # false alarms are costly: up-weight background after balancing
    class_w = torch.tensor(cw, dtype=torch.float32, device=device)

    model = VoiceCNN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-3)
    steps_per_epoch = int(np.ceil(len(y_train) / args.batch))
    total_steps = args.epochs * steps_per_epoch
    warmup = steps_per_epoch  # 1 epoch linear warm-up
    step_count = [0]

    def set_lr():
        # cosine decay driven by max(step progress, wall-clock progress) so the LR is
        # fully annealed even if the time budget ends training before args.epochs
        s = step_count[0]
        prog = max(s / total_steps, (time.time() - t_train) / (60.0 * args.max_minutes))
        lr = args.lr * min(1.0, (s + 1) / warmup) * (0.02 + 0.98 * 0.5 * (1 + np.cos(np.pi * min(1.0, prog))))
        for g in opt.param_groups:
            g["lr"] = lr
        step_count[0] += 1
    Xt, yt, wt = torch.from_numpy(X_train), torch.from_numpy(y_train), torch.from_numpy(w_train)
    Xv, yv = torch.from_numpy(X_val).to(device), torch.from_numpy(y_val).to(device)

    best = {"val_loss": 1e9, "epoch": -1, "state": None}
    history = []
    bad = 0
    t_train = time.time()
    for epoch in range(args.epochs):
        model.train()
        perm = torch.randperm(len(yt))
        tot, correct, n = 0.0, 0, 0
        for i in range(0, len(perm), args.batch):
            idx = perm[i:i + args.batch]
            xb = spec_augment(Xt[idx], rng).to(device)
            yb, wb = yt[idx].to(device), wt[idx].to(device)
            logits = model(xb)
            loss_vec = F.cross_entropy(logits, yb, weight=class_w, reduction="none", label_smoothing=0.0)
            loss = (loss_vec * wb).sum() / (class_w[yb] * wb).sum()
            set_lr()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
            correct += (logits.argmax(1) == yb).sum().item()
            n += len(idx)
        model.eval()
        with torch.no_grad():
            lv = model(Xv)
            val_loss = F.cross_entropy(lv, yv, weight=class_w).item()
            val_acc = (lv.argmax(1) == yv).float().mean().item()
        history.append({"epoch": epoch + 1, "train_loss": tot / n, "train_acc": correct / n,
                        "val_loss": val_loss, "val_acc": val_acc})
        print(f"epoch {epoch + 1:3d}  train_loss {tot / n:.4f} acc {correct / n:.4f}  "
              f"val_loss {val_loss:.4f} acc {val_acc:.4f}  ({time.time() - t_train:.0f}s)", flush=True)
        over_budget = (time.time() - t_train) / 60.0 > args.max_minutes
        if val_loss < best["val_loss"] - 1e-4:
            best = {"val_loss": val_loss, "epoch": epoch + 1,
                    "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}}
            bad = 0
        else:
            bad += 1
            if bad >= args.patience:
                print("early stopping")
                break
        if over_budget:
            print(f"time budget of {args.max_minutes} min reached - stopping")
            break
    train_seconds = time.time() - t_train
    model.load_state_dict(best["state"])
    model = model.cpu().eval()
    device = "cpu"

    results = {}
    for s in ["val", "test_seen", "test_heldout"]:
        m = split == s
        results[s] = evaluate(predict_proba(model, X[m], device), y[m])
    m_test = np.isin(split, ["test_seen", "test_heldout"])
    results["test_all"] = evaluate(predict_proba(model, X[m_test], device), y[m_test])
    if real_test is not None and len(real_test[1]):
        results["test_real"] = evaluate(predict_proba(model, real_test[0], device), real_test[1])

    # ---------------- ONNX export + parity check
    os.makedirs(MODEL_DIR, exist_ok=True)
    onnx_path = os.path.join(MODEL_DIR, "voice_cnn.onnx")
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "voice_cnn.pt"))
    dummy = torch.from_numpy(X[:2])
    torch.onnx.export(model, dummy, onnx_path, input_names=["mfcc"], output_names=["logits"],
                      dynamic_axes={"mfcc": {0: "N"}, "logits": {0: "N"}}, opset_version=17, dynamo=False)
    import onnxruntime as ort
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    check = X[m_test][:256]
    with torch.no_grad():
        ref = model(torch.from_numpy(check)).numpy()
    onx = sess.run(["logits"], {"mfcc": check})[0]
    max_diff = float(np.max(np.abs(ref - onx)))
    print(f"ONNX vs torch max |diff| = {max_diff:.2e}")
    assert max_diff < 1e-4, "ONNX parity check failed"

    lat = latency_benchmark(onnx_path, X[m_test])
    with torch.no_grad():
        x1 = torch.from_numpy(X[:1])
        for _ in range(10):
            model(x1)
        t = time.perf_counter()
        for _ in range(200):
            model(x1)
        lat["torch_cpu_single_window_ms"] = (time.perf_counter() - t) / 200 * 1000

    onnx_size = os.path.getsize(onnx_path)
    labels = {
        "classes": CLASSES,
        "background_class": "background",
        "display": {c: {"keyword": DISPLAY[c][0], "language": DISPLAY[c][1]} for c in CLASSES},
        "threshold": THRESHOLD,
        "feature_params": FEATURE_PARAMS,
        "inference": {"window_seconds": 1.0, "hop_seconds": 0.25, "aggregation": "max over windows of max non-background softmax prob"},
        "input": {"name": "mfcc", "shape": ["N", 1, N_MFCC, N_FRAMES]},
        "output": {"name": "logits", "apply": "softmax"},
        "model_architecture": ARCH,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "training_data": "synthetic multilingual TTS (edge-tts neural voices) + augmentation" +
                         (f" + {len(set(gr))} real recordings" if len(gr) else ""),
        "heldout_voices": HELDOUT_VOICES,
    }
    with open(os.path.join(MODEL_DIR, "voice_cnn_labels.json"), "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)

    os.makedirs(REPORT_DIR, exist_ok=True)
    meta_counts = {c: int((y == i).sum()) for i, c in enumerate(CLASSES)}
    metrics = {
        "generated_at": labels["trained_at"],
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "dataset": {
            "clips_per_class": meta_counts,
            "total_clips": int(len(y)),
            "voices": sorted(set(voices) - {"synthetic"}),
            "heldout_voices": HELDOUT_VOICES,
            "split_sizes": {s: int((split == s).sum()) for s in ["train", "val", "test_seen", "test_heldout"]},
            "real_recordings": len(set(gr)), "real_train_windows": int(real_train_mask.sum()),
            "real_sample_weight": args.real_weight,
        },
        "model": {"architecture": ARCH, "parameters": int(n_params), "onnx_bytes": int(onnx_size),
                  "onnx_opset": 17, "onnx_torch_max_abs_diff": max_diff},
        "training": {"epochs_run": len(history), "best_epoch": best["epoch"], "seconds": train_seconds,
                     "optimizer": "AdamW(wd=1e-3) + 1-epoch warm-up + cosine LR (time-budget aware)", "lr": args.lr, "batch": args.batch,
                     "loss": "class-weighted cross-entropy (inverse frequency, background x2 false-alarm cost), real clips x sample weight",
                     "regularization": "dropout 0.2/0.3, SpecAugment (p=0.6) 1 freq (<=6) + 2 time (<=10) masks",
                     "history": history},
        "results": results,
        "latency": lat,
        "feature_params": FEATURE_PARAMS,
    }
    with open(os.path.join(REPORT_DIR, "voice_cnn_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    write_report(metrics)
    print(json.dumps({k: (v["accuracy"], v["binary_distress_at_threshold"]["f1"]) for k, v in results.items() if v},
                     indent=1))
    print("latency:", json.dumps(lat, indent=1))


def write_report(m):
    L = []
    R = m["results"]
    d = m["dataset"]
    L.append("# SurakshaX Voice-Distress CNN - Evaluation Report\n")
    L.append(f"Generated: {m['generated_at']}  |  device: {m['device']}\n")
    L.append("> **Honesty note:** this model is trained on *synthetic* speech (Microsoft neural TTS voices via "
             "edge-tts) with heavy acoustic augmentation, plus any real clips placed in `ml/data/voice_real/` "
             f"(currently {d['real_recordings']}). Numbers below are measured on synthetic held-out data; accuracy "
             "on real phone recordings of real people (especially screaming/panicked speech) will be lower until "
             "real recordings are added.\n")
    L.append("## Dataset\n")
    L.append("| class | clips |\n|---|---|")
    for c, n in d["clips_per_class"].items():
        L.append(f"| {c} | {n} |")
    L.append(f"\nTotal: {d['total_clips']} clips (1.0 s, 16 kHz). Splits: {d['split_sizes']}.\n")
    L.append(f"Voices ({len(d['voices'])}): {', '.join(d['voices'])}\n")
    L.append(f"Held-out speakers (never seen in training): **{', '.join(d['heldout_voices'])}**\n")
    L.append("## Model\n")
    mm = m["model"]
    L.append(f"- {mm['architecture']}; {mm['parameters']:,} parameters; ONNX opset 17, "
             f"{mm['onnx_bytes'] / 1e6:.2f} MB; ONNX-vs-torch max |diff| {mm['onnx_torch_max_abs_diff']:.1e}")
    L.append(f"- Features: 40-dim MFCC, 25 ms Hamming / 10 ms hop, 1.0 s window (40x101), per-utterance mean/var norm (numpy, `ml/features.py`)")
    t = m["training"]
    L.append(f"- Training: {t['epochs_run']} epochs (best {t['best_epoch']}), {t['seconds']:.0f} s, {t['optimizer']}, {t['regularization']}\n")
    L.append("## Results\n")
    L.append("| split | n | accuracy | macro F1 | distress P @0.85 | distress R @0.85 | distress F1 @0.85 | FPR @0.85 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s, r in R.items():
        if not r:
            continue
        b = r["binary_distress_at_threshold"]
        L.append(f"| {s} | {r['n']} | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | {b['precision']:.4f} | "
                 f"{b['recall']:.4f} | {b['f1']:.4f} | {b['false_positive_rate']:.4f} |")
    L.append("\n`test_seen` = unseen utterances from training voices; `test_heldout` = speakers never seen in training.\n")
    for s in ["test_all", "test_heldout"]:
        r = R.get(s)
        if not r:
            continue
        L.append(f"### Per-class ({s})\n")
        L.append("| class | precision | recall | F1 | support |\n|---|---|---|---|---|")
        for c, v in r["per_class"].items():
            L.append(f"| {c} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1-score']:.3f} | {int(v['support'])} |")
        L.append(f"\nConfusion matrix ({s}; rows = true, cols = predicted; order {', '.join(CLASSES)}):\n")
        L.append("```")
        for c, row in zip(CLASSES, r["confusion_matrix"]):
            L.append(f"{c:>13s} " + " ".join(f"{v:4d}" for v in row))
        L.append("```\n")
    lat = m["latency"]
    L.append("## CPU inference latency\n")
    L.append(f"- ONNX Runtime, 1 thread, one 1 s window: {lat['onnx_single_window_ms']:.2f} ms model + "
             f"{lat['mfcc_single_window_ms']:.2f} ms MFCC = **{lat['end_to_end_single_window_ms']:.2f} ms**")
    L.append(f"- 3 s clip (9 sliding windows, batched): {lat['end_to_end_3s_clip_ms']:.2f} ms")
    L.append(f"- PyTorch CPU single window (training env): {lat['torch_cpu_single_window_ms']:.2f} ms\n")
    with open(os.path.join(REPORT_DIR, "voice_cnn_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
