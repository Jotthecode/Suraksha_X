import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { Accelerometer } from 'expo-sensors';
import { ExpoSpeechRecognitionModule } from 'expo-speech-recognition';
import { useSafety } from './SafetyContext';
import { useVoiceGuard } from '../hooks/useVoiceGuard';
import { navigateTo, navigationRef } from '../navigation/navigationRef';
import { matchTranscript, MAX_PHRASES } from '../utils/phraseMatching';
import { createMotionDetector } from '../utils/motionDetection';
import {
  addSosCountdownListener,
  cancelSosCountdown,
  getSosCountdown,
  isProtectionRunning,
  requestNotificationPermission,
  startProtection,
  startSosCountdown,
  stopProtection,
  supportsNativeCountdown,
} from '../../modules/surakshax-native';

const STORAGE_KEY = 'surakshax_trigger_settings';
const COOLDOWN_MS = 60000; // one automatic SOS per minute at most
const COUNTDOWN_SECONDS = 10;
const START_WATCHDOG_MS = 8000; // a recognition session that hasn't started by then has failed
const FAILURES_PER_STRATEGY = 2;

export const DEFAULT_TRIGGER_SETTINGS = {
  voiceEnabled: false,
  useDistressWords: true, // "Bachao", "Help me", "help… help"
  codePhrases: [], // the user's own secret phrases
  silentCodePhrase: true, // code phrase sends the SOS straight away, without the SOS screen or sound
  shakeEnabled: false,
  runEnabled: false,
  backgroundProtection: true, // keep triggers running while other apps are open / screen is off
  autoCallFirstContact: true, // ring the first emergency contact after a (non-silent) SOS
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

const safeCall = (fn, fallback) => {
  try {
    return fn();
  } catch (e) {
    return fallback;
  }
};

const speechAvailable = () => !!safeCall(() => ExpoSpeechRecognitionModule.isRecognitionAvailable(), false);

const GOOGLE_SPEECH = 'com.google.android.googlequicksearchbox';

/**
 * Recognition setups tried in order. Phones differ a lot: the default recognizer may be Samsung's,
 * Google's may be missing, continuous mode is Android 13+, en-IN may be unavailable offline.
 * Each setup gets FAILURES_PER_STRATEGY attempts to start before the next is tried.
 */
const buildSpeechStrategies = () => {
  if (Platform.OS !== 'android') return [{ label: 'Browser speech', lang: 'en-IN', continuous: true }];
  const services = safeCall(() => ExpoSpeechRecognitionModule.getSpeechRecognitionServices(), []) || [];
  const hasGoogle = services.includes(GOOGLE_SPEECH);
  const onDevice = safeCall(() => ExpoSpeechRecognitionModule.supportsOnDeviceRecognition(), false);
  const list = [];
  if (hasGoogle) {
    list.push({ label: 'Google speech', service: GOOGLE_SPEECH, lang: 'en-IN', continuous: true });
    list.push({ label: 'Google speech (basic)', service: GOOGLE_SPEECH, lang: 'en-US', continuous: false });
  }
  list.push({ label: 'Phone speech service', lang: 'en-IN', continuous: true });
  list.push({ label: 'Phone speech service (basic)', lang: 'en-US', continuous: false });
  if (onDevice) list.push({ label: 'On-device speech', lang: 'en-US', continuous: true, onDevice: true });
  return list;
};

/**
 * Hands-free SOS triggers that run anywhere in the app while logged in, and in the background
 * while the protection service (Android notification) is on:
 *  - Voice: speech-to-text matched against the user's code phrases and distress words.
 *    Falls back to the server voice model (distress words only) when speech recognition fails.
 *  - Motion: hard phone shake, or sudden running (step rate + GPS speed).
 */
export const TriggerProvider = ({ children }) => {
  const { isLoggedIn, executeDispatch } = useSafety();
  const [settings, setSettings] = useState(DEFAULT_TRIGGER_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  // Latest dispatch function without re-subscribing sensors every time the safety state re-renders
  const dispatchRef = useRef(executeDispatch);
  dispatchRef.current = executeDispatch;

  const [voiceMode, setVoiceMode] = useState(null); // 'speech' | 'model' | null
  const [voiceState, setVoiceState] = useState('off'); // off | starting | listening | error
  const [voiceError, setVoiceError] = useState(null);
  const [voiceDebug, setVoiceDebug] = useState({ engine: null, lastError: null, lastHeard: null });
  const [motionState, setMotionState] = useState({ available: null, active: false, error: null });
  const [motionStats, setMotionStats] = useState({ stepsPerMin: 0, speedKmh: null });
  const [lastTrigger, setLastTrigger] = useState(null); // { reason, at, silent }
  const [protectionOn, setProtectionOn] = useState(false);

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
  const dispatchNow = (reason, { silent = false } = {}) =>
    dispatchRef.current(reason, { autoCall: !silent && settingsRef.current.autoCallFirstContact }).catch(() => {});

  const fireRef = useRef(null);
  fireRef.current = (reason, { silent = false } = {}) => {
    const now = Date.now();
    if (now - lastFireRef.current < COOLDOWN_MS) return;
    if (navigationRef.isReady() && navigationRef.getCurrentRoute()?.name === 'AlertsModal') return;
    if (getSosCountdown().running) return;
    lastFireRef.current = now;
    setLastTrigger({ reason, at: now, silent });

    if (silent) {
      // No screen change, sound or vibration: the alert goes out quietly and shows up in SOS history
      dispatchNow(reason, { silent: true });
    } else if (AppState.currentState !== 'active' && supportsNativeCountdown()) {
      // In the background JavaScript timers are paused, so the countdown runs natively as a notification
      startSosCountdown(COUNTDOWN_SECONDS, reason);
    } else {
      navigateTo('AlertsModal', { triggerReason: reason });
    }
  };
  const fire = useCallback((reason, opts) => fireRef.current(reason, opts), []);

  // Native countdown finished (or cancelled with "I'm safe" in the notification)
  useEffect(() => {
    const done = addSosCountdownListener('onSosCountdownFinished', ({ reason }) => dispatchNow(reason));
    return () => done.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Coming back to the app during a background countdown: continue it on the SOS screen
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state !== 'active') return;
      const c = getSosCountdown();
      if (c.running) {
        cancelSosCountdown(false);
        navigateTo('AlertsModal', { triggerReason: c.reason, seconds: Math.max(1, c.remaining) });
      }
      // Speech sessions can't always restart from the background; make sure listening resumes
      if (voiceWantedRef.current && voiceModeRef.current === 'speech' && !sessionStartedRef.current) {
        startSpeechSession();
      }
    });
    return () => sub.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTranscript = (transcript, isFinal) => {
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
  };

  // ---------------------------------------------------------------- voice: server model fallback
  const modelGuard = useVoiceGuard({
    onDistress: (res) => {
      fire(`Voice: "${res.detected_keyword || 'distress'}"`);
      // The model guard stops itself after a detection; resume listening when the cooldown is over
      setTimeout(() => {
        if (voiceWantedRef.current && voiceModeRef.current === 'model') modelGuard.start();
      }, COOLDOWN_MS);
    },
  });

  // ---------------------------------------------------------------- voice: speech recognition
  const voiceModeRef = useRef(null);
  const strategiesRef = useRef([]);
  const strategyIndexRef = useRef(0);
  const failuresRef = useRef(0);
  const sessionStartedRef = useRef(false);
  const watchdogRef = useRef(null);
  const lastErrorRef = useRef(null);

  const setMode = (mode) => {
    voiceModeRef.current = mode;
    setVoiceMode(mode);
  };

  const clearWatchdog = () => {
    if (watchdogRef.current) clearTimeout(watchdogRef.current);
    watchdogRef.current = null;
  };

  const startSpeechSession = () => {
    const strategy = strategiesRef.current[strategyIndexRef.current];
    if (!strategy) return;
    const s = settingsRef.current;
    sessionStartedRef.current = false;
    setVoiceDebug((d) => ({ ...d, engine: strategy.label }));
    try {
      ExpoSpeechRecognitionModule.start({
        lang: strategy.lang,
        interimResults: true,
        continuous: strategy.continuous,
        maxAlternatives: 3,
        requiresOnDeviceRecognition: !!strategy.onDevice,
        androidRecognitionServicePackage: strategy.service,
        contextualStrings: [...s.codePhrases, 'bachao', 'help me', 'save me', 'madad karo'],
        androidIntentOptions: { EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS: 10000 },
      });
    } catch (e) {
      lastErrorRef.current = e.message;
    }
    clearWatchdog();
    watchdogRef.current = setTimeout(() => {
      // Never got 'start': abort, and the 'end' handler counts it as a failure
      if (voiceWantedRef.current && !sessionStartedRef.current) {
        lastErrorRef.current = lastErrorRef.current || 'speech service did not respond';
        safeCall(() => ExpoSpeechRecognitionModule.abort());
      }
    }, START_WATCHDOG_MS);
  };

  const fallBackToModel = async () => {
    safeCall(() => ExpoSpeechRecognitionModule.abort());
    if (Platform.OS === 'web') {
      voiceWantedRef.current = false;
      setVoiceState('error');
      setVoiceError(`Speech recognition isn't working in this browser (${lastErrorRef.current || 'no response'})`);
      return;
    }
    setMode('model');
    const ok = await modelGuard.start();
    setVoiceState(ok ? 'listening' : 'error');
    setVoiceError(
      ok
        ? `Speech-to-text unavailable (${lastErrorRef.current || 'no response'}); using the offline model for "Bachao" / "Help" only`
        : modelGuard.error || 'Could not start the microphone'
    );
  };

  const handleSessionEnd = () => {
    clearWatchdog();
    if (!voiceWantedRef.current || voiceModeRef.current !== 'speech') {
      setVoiceState((state) => (state === 'error' ? state : 'off'));
      return;
    }
    if (sessionStartedRef.current) {
      // Normal end (silence / final result): listen again right away. No timer here, because
      // timers are paused in the background; native events keep flowing.
      failuresRef.current = 0;
      startSpeechSession();
      return;
    }
    // The session failed before it started listening
    failuresRef.current += 1;
    if (failuresRef.current >= FAILURES_PER_STRATEGY) {
      failuresRef.current = 0;
      strategyIndexRef.current += 1;
      if (strategyIndexRef.current >= strategiesRef.current.length) {
        fallBackToModel();
        return;
      }
    }
    setVoiceError(lastErrorRef.current ? `Retrying speech (${lastErrorRef.current})` : null);
    if (AppState.currentState === 'active') setTimeout(() => voiceWantedRef.current && startSpeechSession(), 500);
    else startSpeechSession();
  };

  useEffect(() => {
    const subs = [
      ExpoSpeechRecognitionModule.addListener('start', () => {
        sessionStartedRef.current = true;
        clearWatchdog();
        lastErrorRef.current = null;
        setVoiceState('listening');
        setVoiceError(null);
      }),
      ExpoSpeechRecognitionModule.addListener('result', (event) => {
        const results = event.results || [];
        if (results[0]?.transcript) setVoiceDebug((d) => ({ ...d, lastHeard: results[0].transcript }));
        for (const r of results) handleTranscript(r.transcript, !!event.isFinal);
      }),
      ExpoSpeechRecognitionModule.addListener('error', (event) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          voiceWantedRef.current = false;
          clearWatchdog();
          setVoiceState('error');
          setVoiceError('Microphone or speech permission was denied');
          return;
        }
        // 'no-speech' / 'speech-timeout' / 'nomatch' are normal pauses, not failures
        if (!['no-speech', 'speech-timeout', 'nomatch', 'aborted'].includes(event.error)) {
          lastErrorRef.current = event.message ? `${event.error}: ${event.message}` : event.error;
          setVoiceDebug((d) => ({ ...d, lastError: lastErrorRef.current }));
        }
      }),
      ExpoSpeechRecognitionModule.addListener('end', handleSessionEnd),
    ];
    return () => subs.forEach((s) => s.remove());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startVoice = async () => {
    voiceWantedRef.current = true;
    setVoiceState('starting');
    setVoiceError(null);
    lastErrorRef.current = null;
    if (speechAvailable()) {
      const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync().catch(() => ({ granted: false }));
      if (!perm.granted) {
        voiceWantedRef.current = false;
        setVoiceState('error');
        setVoiceError('Allow microphone access to use voice SOS');
        return false;
      }
      strategiesRef.current = buildSpeechStrategies();
      strategyIndexRef.current = 0;
      failuresRef.current = 0;
      setMode('speech');
      startSpeechSession();
      return true;
    }
    lastErrorRef.current = 'no speech recognition service on this phone';
    await fallBackToModel();
    return voiceWantedRef.current;
  };

  const stopVoice = () => {
    voiceWantedRef.current = false;
    clearWatchdog();
    safeCall(() => ExpoSpeechRecognitionModule.abort());
    modelGuard.stop();
    setMode(null);
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
    if (voiceModeRef.current === 'speech' && voiceWantedRef.current && sessionStartedRef.current) {
      safeCall(() => ExpoSpeechRecognitionModule.stop()); // 'end' restarts it with the new phrases
    }
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

  // ---------------------------------------------------------------- background protection service
  const anyTrigger = settings.voiceEnabled || settings.shakeEnabled || settings.runEnabled;
  const wantProtection = Platform.OS === 'android' && loaded && isLoggedIn && settings.backgroundProtection && anyTrigger;
  const micReady = settings.voiceEnabled && voiceState === 'listening';

  useEffect(() => {
    let cancelled = false;
    if (!wantProtection) {
      if (isProtectionRunning()) stopProtection();
      setProtectionOn(false);
      return undefined;
    }
    (async () => {
      await requestNotificationPermission();
      if (cancelled) return;
      // Restarted when the microphone becomes ready, so the service is allowed to keep it in the background
      startProtection('SurakshaX', 'Protection is on', { mic: micReady, location: true });
      setTimeout(() => !cancelled && setProtectionOn(isProtectionRunning()), 1500);
    })();
    return () => {
      cancelled = true;
    };
  }, [wantProtection, micReady]);

  // ---------------------------------------------------------------- status
  const voiceStatus =
    voiceState === 'off'
      ? null
      : voiceState === 'starting'
      ? voiceError || 'Starting…'
      : voiceState === 'error'
      ? voiceError
      : voiceMode === 'model'
      ? voiceError || 'Listening for "Bachao" / "Help"'
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
        voiceDebug,
        speechSupported: speechAvailable(),
        motionState,
        motionStats,
        lastTrigger,
        protectionOn,
      }}
    >
      {children}
    </TriggerContext.Provider>
  );
};

export const useTriggers = () => useContext(TriggerContext);
