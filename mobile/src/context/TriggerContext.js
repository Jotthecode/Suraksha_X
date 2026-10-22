import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { Accelerometer } from 'expo-sensors';
import { ExpoSpeechRecognitionModule } from 'expo-speech-recognition';
import { useSafety } from './SafetyContext';
import { useVoiceGuard } from '../hooks/useVoiceGuard';
import { navigateTo, navigationRef } from '../navigation/navigationRef';
import { matchTranscript, MAX_PHRASES } from '../utils/phraseMatching';
import { createMotionDetector } from '../utils/motionDetection';

const STORAGE_KEY = 'surakshax_trigger_settings';
const COOLDOWN_MS = 60000; // one automatic SOS per minute at most
const RESTART_DELAY_MS = 600;

export const DEFAULT_TRIGGER_SETTINGS = {
  voiceEnabled: false,
  useDistressWords: true, // "Bachao", "Help me", "help… help"
  codePhrases: [], // the user's own secret phrases
  silentCodePhrase: true, // code phrase sends the SOS straight away, without the SOS screen or sound
  shakeEnabled: false,
  runEnabled: false,
};

const TriggerContext = createContext(null);

const STANDARD_GRAVITY = 9.80665;

/**
 * Acceleration in g (x, y, z incl. gravity, ~1 g at rest), ~20 Hz.
 * Returns { remove }, { denied: true } (browser refused motion access) or null if unavailable.
 * On the web, expo-sensors' Accelerometer reports device *orientation* angles, so the browser's
 * devicemotion event (m/s²) is read directly instead.
 */
const subscribeAcceleration = async (onSample) => {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined' || typeof DeviceMotionEvent === 'undefined') return null;
    // iOS Safari asks for permission (only allowed from a user gesture, e.g. the switch tap)
    if (typeof DeviceMotionEvent.requestPermission === 'function') {
      const result = await DeviceMotionEvent.requestPermission().catch(() => 'denied');
      if (result !== 'granted') return { denied: true };
    }
    let last = 0;
    const handler = (e) => {
      const a = e.accelerationIncludingGravity;
      const now = Date.now();
      if (!a || a.x == null || a.y == null || a.z == null || now - last < 45) return;
      last = now;
      onSample({ x: a.x / STANDARD_GRAVITY, y: a.y / STANDARD_GRAVITY, z: a.z / STANDARD_GRAVITY });
    };
    window.addEventListener('devicemotion', handler);
    return { remove: () => window.removeEventListener('devicemotion', handler) };
  }
  const available = await Accelerometer.isAvailableAsync().catch(() => false);
  if (!available) return null;
  Accelerometer.setUpdateInterval(50);
  return Accelerometer.addListener(onSample);
};

const speechAvailable = () => {
  try {
    return !!ExpoSpeechRecognitionModule.isRecognitionAvailable();
  } catch (e) {
    return false;
  }
};

/**
 * Hands-free SOS triggers that run anywhere in the app while logged in:
 *  - Voice: on-device speech-to-text matched against the user's code phrases and distress words.
 *    Falls back to the server voice model (distress words only) on devices without a speech service.
 *  - Motion: hard phone shake, or sudden running (step rate + GPS speed).
 */
export const TriggerProvider = ({ children }) => {
  const { isLoggedIn, executeDispatch } = useSafety();
  const [settings, setSettings] = useState(DEFAULT_TRIGGER_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const [voiceMode, setVoiceMode] = useState(null); // 'speech' | 'model' | null
  const [voiceState, setVoiceState] = useState('off'); // off | starting | listening | error
  const [voiceError, setVoiceError] = useState(null);
  const [motionState, setMotionState] = useState({ available: null, active: false, error: null });
  const [motionStats, setMotionStats] = useState({ stepsPerMin: 0, speedKmh: null });
  const [lastTrigger, setLastTrigger] = useState(null); // { reason, at, silent }

  const lastFireRef = useRef(0);
  const voiceWantedRef = useRef(false);
  const weakHitsRef = useRef({});

  // ---------------------------------------------------------------- settings
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        if (raw) setSettings({ ...DEFAULT_TRIGGER_SETTINGS, ...JSON.parse(raw) });
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const updateSettings = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      next.codePhrases = (next.codePhrases || []).slice(0, MAX_PHRASES);
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  // ---------------------------------------------------------------- firing
  const fire = useCallback(
    async (reason, { silent = false } = {}) => {
      const now = Date.now();
      if (now - lastFireRef.current < COOLDOWN_MS) return;
      if (navigationRef.isReady() && navigationRef.getCurrentRoute()?.name === 'AlertsModal') return;
      lastFireRef.current = now;
      setLastTrigger({ reason, at: now, silent });
      if (silent) {
        // No screen change, sound or vibration: the alert goes out quietly and shows up in SOS history
        executeDispatch(reason).catch(() => {});
      } else {
        navigateTo('AlertsModal', { triggerReason: reason });
      }
    },
    [executeDispatch]
  );

  const handleTranscript = useCallback(
    (transcript, isFinal) => {
      const s = settingsRef.current;
      const match = matchTranscript(transcript, {
        codePhrases: s.codePhrases,
        useDistressWords: s.useDistressWords,
        weakHits: weakHitsRef.current,
        isFinal,
      });
      if (!match) return;
      if (match.type === 'code') {
        // The SMS says "code phrase", never the phrase itself
        fire('Voice code phrase', { silent: s.silentCodePhrase });
      } else {
        fire(`Voice: "${match.word}"`);
      }
    },
    [fire]
  );

  // ---------------------------------------------------------------- voice: server model fallback
  const modelGuard = useVoiceGuard({
    onDistress: (res) => {
      fire(`Voice: "${res.detected_keyword || 'distress'}"`);
      // The model guard stops itself after a detection; resume listening if still wanted
      setTimeout(() => {
        if (voiceWantedRef.current && voiceMode === 'model') modelGuard.start();
      }, COOLDOWN_MS);
    },
  });

  // ---------------------------------------------------------------- voice: speech recognition
  useEffect(() => {
    const subs = [
      ExpoSpeechRecognitionModule.addListener('start', () => {
        setVoiceState('listening');
        setVoiceError(null);
      }),
      ExpoSpeechRecognitionModule.addListener('result', (event) => {
        for (const r of event.results || []) handleTranscript(r.transcript, !!event.isFinal);
      }),
      ExpoSpeechRecognitionModule.addListener('error', (event) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          voiceWantedRef.current = false;
          setVoiceState('error');
          setVoiceError('Microphone or speech permission was denied');
        }
        // 'no-speech', 'network', 'aborted' etc. end the session; the 'end' handler restarts it
      }),
      ExpoSpeechRecognitionModule.addListener('end', () => {
        if (voiceWantedRef.current) {
          // Recognition sessions end on silence or after a final result; keep listening
          setTimeout(() => voiceWantedRef.current && startSpeechSession(), RESTART_DELAY_MS);
        } else {
          // Keep a permission error visible; 'end' always follows 'error'
          setVoiceState((state) => (state === 'error' ? state : 'off'));
        }
      }),
    ];
    return () => subs.forEach((s) => s.remove());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleTranscript]);

  const startSpeechSession = () => {
    const s = settingsRef.current;
    try {
      ExpoSpeechRecognitionModule.start({
        lang: 'en-IN',
        interimResults: true,
        continuous: true,
        maxAlternatives: 3,
        contextualStrings: [...s.codePhrases, 'bachao', 'help me', 'save me', 'madad karo'],
        androidIntentOptions: { EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS: 10000 },
      });
    } catch (e) {
      setVoiceState('error');
      setVoiceError(e.message);
    }
  };

  const startVoice = async () => {
    voiceWantedRef.current = true;
    setVoiceState('starting');
    setVoiceError(null);
    if (speechAvailable()) {
      const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync().catch(() => ({ granted: false }));
      if (!perm.granted) {
        voiceWantedRef.current = false;
        setVoiceState('error');
        setVoiceError('Allow microphone access to use voice SOS');
        return false;
      }
      setVoiceMode('speech');
      startSpeechSession();
      return true;
    }
    if (Platform.OS !== 'web') {
      // No speech service on this phone: distress words via the server voice model (code phrases need speech-to-text)
      setVoiceMode('model');
      const ok = await modelGuard.start();
      setVoiceState(ok ? 'listening' : 'error');
      if (!ok) setVoiceError(modelGuard.error || 'Could not start the microphone');
      return ok;
    }
    voiceWantedRef.current = false;
    setVoiceState('error');
    setVoiceError('Voice recognition needs Chrome or Edge in the browser');
    return false;
  };

  const stopVoice = () => {
    voiceWantedRef.current = false;
    try {
      ExpoSpeechRecognitionModule.abort();
    } catch (e) {}
    modelGuard.stop();
    setVoiceMode(null);
    setVoiceState('off');
  };

  // Follow the setting (and log-in state)
  useEffect(() => {
    if (!loaded) return;
    if (isLoggedIn && settings.voiceEnabled) {
      if (!voiceWantedRef.current) {
        startVoice().then((ok) => {
          if (!ok) updateSettings({ voiceEnabled: false });
        });
      }
    } else if (voiceWantedRef.current || voiceState !== 'off') {
      stopVoice();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, isLoggedIn, settings.voiceEnabled]);

  // New code phrases take effect in the next recognition session
  useEffect(() => {
    if (voiceMode === 'speech' && voiceWantedRef.current) {
      try {
        ExpoSpeechRecognitionModule.stop(); // 'end' restarts it with the new contextual strings
      } catch (e) {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.codePhrases]);

  // ---------------------------------------------------------------- motion
  useEffect(() => {
    if (!loaded || !isLoggedIn || (!settings.shakeEnabled && !settings.runEnabled)) {
      setMotionState((m) => ({ ...m, active: false }));
      return undefined;
    }
    let accelSub = null;
    let locSub = null;
    let statsTimer = null;
    let noDataTimer = null;
    let cancelled = false;

    const detector = createMotionDetector({
      onShake: settings.shakeEnabled ? (reason) => fire(reason) : null,
      onRun: settings.runEnabled ? (reason) => fire(reason) : null,
    });

    (async () => {
      let gotSample = false;
      const onSample = (s) => {
        // Desktop browsers send an event with empty (null) readings
        if (!Number.isFinite(s.x) || !Number.isFinite(s.y) || !Number.isFinite(s.z)) return;
        gotSample = true;
        detector.push(s, Date.now());
      };
      accelSub = await subscribeAcceleration(onSample);
      if (cancelled) {
        accelSub?.remove();
        return;
      }
      if (!accelSub || accelSub.denied) {
        const error = accelSub?.denied
          ? 'Motion access not allowed. Turn the switch off and on again, then tap Allow.'
          : 'Motion sensor not available on this device';
        accelSub = null;
        setMotionState({ available: false, active: false, error });
        return;
      }
      setMotionState({ available: true, active: true, error: null });
      // Desktop browsers expose the motion API but never send readings
      noDataTimer = setTimeout(() => {
        if (!gotSample && !cancelled) {
          setMotionState({ available: false, active: false, error: 'No motion sensor readings on this device' });
        }
      }, 3000);

      if (settings.runEnabled) {
        try {
          const perm = await Location.getForegroundPermissionsAsync();
          if (perm.granted && !cancelled) {
            locSub = await Location.watchPositionAsync(
              { accuracy: Location.Accuracy.Balanced, timeInterval: 2000, distanceInterval: 0 },
              (loc) => detector.pushSpeed(loc.coords.speed, Date.now())
            );
          }
        } catch (e) {} // without GPS, running is judged from steps alone
        statsTimer = setInterval(() => setMotionStats(detector.stats()), 2000);
      }
    })();

    return () => {
      cancelled = true;
      accelSub?.remove();
      locSub?.remove?.();
      if (statsTimer) clearInterval(statsTimer);
      if (noDataTimer) clearTimeout(noDataTimer);
    };
  }, [loaded, isLoggedIn, settings.shakeEnabled, settings.runEnabled, fire]);

  const voiceStatus =
    voiceState === 'off'
      ? null
      : voiceState === 'starting'
      ? 'Starting…'
      : voiceState === 'error'
      ? voiceError
      : voiceMode === 'model'
      ? 'Listening for distress words'
      : settings.codePhrases.length
      ? `Listening · ${settings.codePhrases.length} code phrase${settings.codePhrases.length > 1 ? 's' : ''}`
      : 'Listening';

  return (
    <TriggerContext.Provider
      value={{
        settings,
        updateSettings,
        voiceMode,
        voiceState,
        voiceStatus,
        speechSupported: speechAvailable(),
        motionState,
        motionStats,
        lastTrigger,
      }}
    >
      {children}
    </TriggerContext.Provider>
  );
};

export const useTriggers = () => useContext(TriggerContext);
