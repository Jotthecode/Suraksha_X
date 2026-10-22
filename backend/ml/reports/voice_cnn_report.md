# SurakshaX Voice-Distress CNN - Evaluation Report

Generated: 2026-10-11T19:44:37.603180+00:00  |  device: cpu

> **Honesty note:** this model is trained on *synthetic* speech (Microsoft neural TTS voices via edge-tts) with heavy acoustic augmentation, plus any real clips placed in `ml/data/voice_real/` (currently 0). Numbers below are measured on synthetic held-out data; accuracy on real phone recordings of real people (especially screaming/panicked speech) will be lower until real recordings are added.

## Dataset

| class | clips |
|---|---|
| help | 688 |
| save_me | 688 |
| emergency | 688 |
| bachao | 672 |
| madad_karo | 688 |
| madat_kara | 688 |
| vachva | 660 |
| kapaathu | 656 |
| sahajjo_koro | 688 |
| background | 1923 |

Total: 8039 clips (1.0 s, 16 kHz). Splits: {'train': 5623, 'val': 935, 'test_seen': 929, 'test_heldout': 552}.

Voices (43): bn-IN-BashkarNeural, bn-IN-TanishaaNeural, en-GB-LibbyNeural, en-GB-MaisieNeural, en-GB-RyanNeural, en-GB-SoniaNeural, en-GB-ThomasNeural, en-IN-NeerjaExpressiveNeural, en-IN-NeerjaNeural, en-IN-PrabhatNeural, en-US-AnaNeural, en-US-AndrewMultilingualNeural, en-US-AndrewNeural, en-US-AriaNeural, en-US-AvaMultilingualNeural, en-US-AvaNeural, en-US-BrianMultilingualNeural, en-US-BrianNeural, en-US-ChristopherNeural, en-US-EmmaMultilingualNeural, en-US-EmmaNeural, en-US-EricNeural, en-US-GuyNeural, en-US-JennyNeural, en-US-MichelleNeural, en-US-RogerNeural, en-US-SteffanNeural, gu-IN-DhwaniNeural, gu-IN-NiranjanNeural, hi-IN-MadhurNeural, hi-IN-SwaraNeural, kn-IN-GaganNeural, kn-IN-SapnaNeural, ml-IN-MidhunNeural, ml-IN-SobhanaNeural, mr-IN-AarohiNeural, mr-IN-ManoharNeural, ta-IN-PallaviNeural, ta-IN-ValluvarNeural, te-IN-MohanNeural, te-IN-ShrutiNeural, ur-IN-GulNeural, ur-IN-SalmanNeural

Held-out speakers (never seen in training): **hi-IN-SwaraNeural, en-GB-RyanNeural, ta-IN-ValluvarNeural**

## Model

- 4-Layer CNN (2x Conv2D + BatchNorm + ReLU + MaxPool, 2x FC, Softmax); 839,626 parameters; ONNX opset 17, 3.36 MB; ONNX-vs-torch max |diff| 5.7e-06
- Features: 40-dim MFCC, 25 ms Hamming / 10 ms hop, 1.0 s window (40x101), per-utterance mean/var norm (numpy, `ml/features.py`)
- Training: 51 epochs (best 36), 2422 s, AdamW(wd=1e-3) + 1-epoch warm-up + cosine LR (time-budget aware), dropout 0.2/0.3, SpecAugment (p=0.6) 1 freq (<=6) + 2 time (<=10) masks

## Results

| split | n | accuracy | macro F1 | distress P @0.85 | distress R @0.85 | distress F1 @0.85 | FPR @0.85 |
|---|---|---|---|---|---|---|---|
| val | 935 | 0.7348 | 0.7542 | 0.9730 | 0.5085 | 0.6679 | 0.0444 |
| test_seen | 929 | 0.7438 | 0.7518 | 0.9824 | 0.4691 | 0.6350 | 0.0276 |
| test_heldout | 552 | 0.7536 | 0.7700 | 0.9795 | 0.5532 | 0.7071 | 0.0417 |
| test_all | 1481 | 0.7475 | 0.7590 | 0.9812 | 0.5009 | 0.6632 | 0.0326 |

`test_seen` = unseen utterances from training voices; `test_heldout` = speakers never seen in training.

### Per-class (test_all)

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| help | 0.756 | 0.703 | 0.729 | 128 |
| save_me | 0.843 | 0.758 | 0.798 | 128 |
| emergency | 0.866 | 0.805 | 0.834 | 128 |
| bachao | 0.702 | 0.675 | 0.688 | 126 |
| madad_karo | 0.705 | 0.727 | 0.715 | 128 |
| madat_kara | 0.667 | 0.688 | 0.677 | 128 |
| vachva | 0.759 | 0.873 | 0.812 | 126 |
| kapaathu | 0.692 | 0.798 | 0.742 | 124 |
| sahajjo_koro | 0.942 | 0.891 | 0.916 | 128 |
| background | 0.683 | 0.677 | 0.680 | 337 |

Confusion matrix (test_all; rows = true, cols = predicted; order help, save_me, emergency, bachao, madad_karo, madat_kara, vachva, kapaathu, sahajjo_koro, background):

```
         help   90    3    2    3    0    1    3    9    0   17
      save_me    0   97    1    1    1    2    0    0    0   26
    emergency    0    1  103    1    1    1    0    6    1   14
       bachao    4    0    0   85    6    7    9    5    0   10
   madad_karo    4    0    0    5   93   18    0    1    2    5
   madat_kara    2    0    1    0   15   88    7    3    0   12
       vachva    0    0    2    1    2    3  110    2    0    6
     kapaathu    3    1    1    2    3    1    3   99    0   11
 sahajjo_koro    1    0    1    5    2    0    0    0  114    5
   background   15   13    8   18    9   11   13   18    4  228
```

### Per-class (test_heldout)

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| help | 0.780 | 0.667 | 0.719 | 48 |
| save_me | 0.881 | 0.771 | 0.822 | 48 |
| emergency | 0.872 | 0.854 | 0.863 | 48 |
| bachao | 0.750 | 0.688 | 0.717 | 48 |
| madad_karo | 0.778 | 0.729 | 0.753 | 48 |
| madat_kara | 0.607 | 0.708 | 0.654 | 48 |
| vachva | 0.698 | 0.917 | 0.793 | 48 |
| kapaathu | 0.746 | 0.917 | 0.822 | 48 |
| sahajjo_koro | 0.918 | 0.938 | 0.928 | 48 |
| background | 0.670 | 0.592 | 0.628 | 120 |

Confusion matrix (test_heldout; rows = true, cols = predicted; order help, save_me, emergency, bachao, madad_karo, madat_kara, vachva, kapaathu, sahajjo_koro, background):

```
         help   32    2    1    2    0    1    2    2    0    6
      save_me    0   37    0    1    0    1    0    0    0    9
    emergency    0    0   41    0    1    0    0    0    1    5
       bachao    2    0    0   33    0    3    5    2    0    3
   madad_karo    0    0    0    1   35    9    0    0    1    2
   madat_kara    0    0    0    0    4   34    5    2    0    3
       vachva    0    0    1    0    0    1   44    0    0    2
     kapaathu    0    0    0    0    0    0    0   44    0    4
 sahajjo_koro    0    0    0    0    2    0    0    0   45    1
   background    7    3    4    7    3    7    7    9    2   71
```

## CPU inference latency

- ONNX Runtime, 1 thread, one 1 s window: 2.44 ms model + 5.62 ms MFCC = **8.06 ms**
- 3 s clip (9 sliding windows, batched): 56.22 ms
- PyTorch CPU single window (training env): 11.98 ms
