# SurakshaX ML pipeline

This folder holds the training code for the two models the backend serves:

| model | served by | artifact | training script |
|---|---|---|---|
| Voice-distress keyword CNN (paper Section IV-C) | `voice_engine.py` | `backend/models/voice_cnn.onnx` + `voice_cnn_labels.json` | `train_voice_cnn.py` |
| Crime-risk Random Forest (India-wide, OSM features) | `crime_model.py` | `backend/crime_rf_model.joblib` | `train_crime_model.py` |

Evaluation reports are in `reports/` (`voice_cnn_report.md`, `crime_rf_report.md` plus JSON metrics).

## Please read first: what these models are trained on

* **The voice CNN is trained on synthetic speech.** Clips come from Microsoft neural text-to-speech
  voices (through `edge-tts`) in English, Hindi, Marathi, Tamil, Bengali, Gujarati, Telugu, Kannada,
  Malayalam and Urdu. Augmentation then adds noise, babble, reverb, phone/AAC band-limiting and
  speed/pitch changes. Its reported accuracy is measured on held-out *synthetic* clips, including
  3 TTS speakers it never saw in training. Real people shouting in panic, children's voices, heavy
  accents and real phone microphones all differ from TTS. **Expect lower accuracy in the real world
  until you add real recordings** (see below). Never use this model as the only SOS trigger. Keep the
  manual SOS button.
* **The crime model uses synthetic labels.** `crime_model.generate_training_data()` samples
  location-independent features (time, street lighting, activity, police distance) and labels them
  with a documented heuristic (`_ground_truth_risk`). The labels do **not** come from real police/FIR
  records. At runtime the features are measured from OpenStreetMap anywhere in India. The metrics
  show how well the Random Forest recovers the heuristic.

## Setup (training machine)

```
pip install torch librosa soundfile numpy scipy scikit-learn edge-tts av onnx onnxruntime
```

The server needs only `numpy`, `onnxruntime` and `av` (see `backend/requirements.txt`). It does
**not** import torch or librosa at inference. The MFCC front-end (`features.py`) is pure numpy, and
training and serving use the exact same function.

## 1. Regenerate the voice dataset

```
python backend/ml/generate_voice_dataset.py            # ~10 min (needs internet for edge-tts)
python backend/ml/generate_voice_dataset.py --quick    # tiny build to test the pipeline
```

* Output: `ml/data/voice/<class>/*.wav` (1.0 s, 16 kHz mono) plus `ml/data/voice/metadata.csv`
  (voice, utterance id and text for every clip).
* Classes: `help, save_me, emergency, bachao, madad_karo, madat_kara, vachva, kapaathu, sahajjo_koro, background`.
* Raw TTS mp3s are cached in `ml/data/tts_cache/`, so a rerun only redoes the augmentation.
* Without internet, or if edge-tts fails for most requests, the script falls back to the Windows SAPI
  voices (`System.Speech`) through PowerShell. You can force this with `--force-sapi`.
* Options: `--keyword-target` (clips per keyword class), `--bg-target`, `--bg-per-voice`,
  `--prosody-variants`, `--workers`.
* Everything in `ml/data/` is git-ignored. Regenerate it; don't commit it.

## 2. Train, evaluate and export

```
python backend/ml/train_voice_cnn.py --epochs 40 --max-minutes 20
```

* Features: 40 MFCC Ã— 101 frames (25 ms Hamming window, 10 ms hop, 1 s window) with per-utterance mean/variance normalization.
* Model: 2Ã— [Conv2D + BatchNorm + ReLU + MaxPool] â†’ FC(128) â†’ FC(10), with dropout and SpecAugment.
  Training uses class-weighted cross-entropy, AdamW, warm-up plus a cosine LR schedule and early
  stopping on validation loss. It runs on the GPU when one is available and on CPU otherwise.
* Splits: the voices in `HELDOUT_VOICES` (`generate_voice_dataset.py`) are excluded from training
  and form `test_heldout`, the speaker-generalisation test. The other utterances are split 75/12.5/12.5
  into train/val/test_seen, stratified by class and grouped by source utterance. Augmented copies of
  one TTS clip therefore never cross splits.
* Writes `backend/models/voice_cnn.onnx` (opset 17, input `mfcc` [N,1,40,101], output `logits`).
  It checks the ONNX output against torch (max |diff| < 1e-4) with onnxruntime.
* Also writes `voice_cnn_labels.json` (classes, display names, feature params, threshold 0.85),
  `voice_cnn.pt`, and the reports in `ml/reports/`.

Then check the deployed model end-to-end:

```
python backend/ml/smoke_test_voice.py
```

## 3. Add REAL recordings (the most useful thing you can do)

Put recordings into `backend/ml/data/voice_real/<class>/`. The class names are the ones listed above.

```
backend/ml/data/voice_real/
    bachao/        priya_01.m4a  rahul_shout.wav  ...
    help/          ...
    background/    street_walk_5min.m4a  office_chatter.webm  ...
```

* Any format works: wav, m4a/AAC (Android recorder), 3gp/AMR, webm/ogg Opus (browser
  MediaRecorder), mp3. Files are decoded with PyAV at 16 kHz mono.
* **Keyword clips:** one utterance per file, ideally 0.5â€“2 s (silence gets trimmed). The keyword
  should be at the end if the clip has extra words. Each file becomes 1 clean window and 8 augmented
  windows (`--real-aug`).
* **Background clips:** any length. Long ambient recordings (street, bus, market, TV, ordinary
  conversation) are especially valuable for cutting false alarms. Each one is cut into many 1 s crops.
* Real windows get **3Ã— sample weight** in the loss (`--real-weight`).
* When there are at least 10 real files, 20% of them are held out as a `test_real` split. This is
  the number to trust for real-world accuracy.
* Then retrain: `python backend/ml/train_voice_cnn.py`. You don't need to regenerate the synthetic data.
* Aim for many different speakers (male and female, young and old), different phones, and
  environments that are both quiet and noisy. Include shouted/panicked deliveries and the regional
  pronunciations you expect. Get consent from everyone you record.

## 4. Crime model

```
python backend/ml/train_crime_model.py
```

This runs a stratified 80/20 evaluation (weighted F1, macro OvR AUC-ROC, per-class report, confusion
matrix) and writes the reports. It then refits on all samples, with the same RF hyper-parameters as
`crime_model.py`, and overwrites `backend/crime_rf_model.joblib`.

## Runtime API (`backend/voice_engine.py`)

```python
from voice_engine import get_voice_classifier
clf = get_voice_classifier()
clf.classify_audio_file("clip.m4a")                    # real CNN on audio
clf.classify_audio_bytes(data, suffix=".webm")         # uploaded bytes
clf.classify_audio_phrase("bachao", 0.8, "street")     # transcript keyword fallback ("source": "keyword_text")
```

Audio results include `sos_triggered`, `posterior_probability`, `detected_keyword`, `language`,
`noise_condition`, `snr_db`, `inference_latency_ms`, `class_probabilities`, `windows_evaluated`,
`audio_duration_s`, `rms_level` and `source` (`"cnn_audio"`, or `"unavailable"` when the model or
onnxruntime is missing).
