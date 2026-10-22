import { useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import {
  useAudioRecorder,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  IOSOutputFormat,
  AudioQuality,
} from 'expo-audio';
import { classifyVoiceAudio } from '../api/config';

// 16 kHz mono AAC: matches the CNN's input rate and keeps uploads small (~12 KB per window)
const VOICE_RECORDING_OPTIONS = {
  extension: '.m4a',
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 32000,
  isMeteringEnabled: true,
  android: { outputFormat: 'mpeg4', audioEncoder: 'aac' },
  ios: { outputFormat: IOSOutputFormat.MPEG4AAC, audioQuality: AudioQuality.MEDIUM },
  web: { mimeType: 'audio/webm', bitsPerSecond: 32000 },
};

const WINDOW_MS = 3000;
// Clips whose loudest moment stays below this level (dBFS) are treated as silence and not uploaded
const SILENCE_DB = -45;
// The CNN flags ~7% of ordinary speech windows at its 0.85 threshold, so one borderline window
// is not enough: trigger on a very confident window, or on two consecutive positive windows
// (people in distress usually repeat the word: "bachao, bachao").
const CONFIDENT_P = 0.95;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Hands-free distress detection: records the microphone in 3-second windows and
 * sends each non-silent window to the backend CNN (/voice_sos). Calls onDistress(result)
 * when the model's posterior crosses its threshold.
 */
export const useVoiceGuard = ({ onDistress }) => {
  const recorder = useAudioRecorder(VOICE_RECORDING_OPTIONS);
  const [isActive, setIsActive] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const activeRef = useRef(false);
  const onDistressRef = useRef(onDistress);
  const lastPositiveRef = useRef(0); // window index of the previous positive
  const windowIndexRef = useRef(0);
  onDistressRef.current = onDistress;

  useEffect(() => () => {
    activeRef.current = false;
  }, []);

  const recordWindow = async () => {
    await recorder.prepareToRecordAsync();
    recorder.record();
    let peakDb = -160;
    let meteringSeen = false;
    const steps = WINDOW_MS / 250;
    for (let i = 0; i < steps && activeRef.current; i++) {
      await sleep(250);
      const m = recorder.getStatus()?.metering;
      if (typeof m === 'number') {
        meteringSeen = true;
        peakDb = Math.max(peakDb, m);
      }
    }
    await recorder.stop();
    return { uri: recorder.uri, silent: meteringSeen && peakDb < SILENCE_DB, peakDb };
  };

  const loop = async () => {
    while (activeRef.current) {
      try {
        const { uri, silent, peakDb } = await recordWindow();
        if (!activeRef.current) break;
        const windowIndex = ++windowIndexRef.current;
        if (!uri || silent) {
          setLastResult({ silent: true, peakDb });
          continue;
        }
        // Upload in the background so the next window starts recording immediately
        classifyVoiceAudio(uri)
          .then((res) => {
            setLastResult({ ...res, peakDb });
            if (!res || !res.sos_triggered) return;
            const confident = (res.posterior_probability || 0) >= CONFIDENT_P;
            const repeated = lastPositiveRef.current > 0 && windowIndex - lastPositiveRef.current <= 1;
            lastPositiveRef.current = windowIndex;
            if ((confident || repeated) && activeRef.current) {
              activeRef.current = false;
              setIsActive(false);
              onDistressRef.current && onDistressRef.current(res);
            }
          })
          .catch((e) => setError(e.message));
      } catch (e) {
        setError(e.message);
        await sleep(1000);
      }
    }
    try {
      await setAudioModeAsync({ allowsRecording: false });
    } catch (e) {}
  };

  const start = async () => {
    if (activeRef.current) return true;
    setError(null);
    const perm = await requestRecordingPermissionsAsync();
    if (!perm.granted) {
      setError('Microphone permission denied');
      return false;
    }
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    activeRef.current = true;
    lastPositiveRef.current = 0;
    windowIndexRef.current = 0;
    setIsActive(true);
    loop();
    return true;
  };

  const stop = () => {
    activeRef.current = false;
    setIsActive(false);
  };

  return { isActive, lastResult, error, start, stop, supported: Platform.OS !== 'web' };
};
