// Shake and sudden-running detection from accelerometer samples (units: g, ~1 g at rest).

// Shake: several hard jolts in quick succession (a deliberate, vigorous shake)
export const SHAKE_G = 2.7;
export const SHAKE_JOLTS = 4;
export const SHAKE_WINDOW_MS = 2000;
const JOLT_GAP_MS = 120;

// Steps: a peak above STEP_HIGH_G after dropping below STEP_LOW_G (hysteresis), at most ~4 steps/s
const STEP_HIGH_G = 1.25;
const STEP_LOW_G = 1.05;
const STEP_MIN_GAP_MS = 250;

// Running: sustained high cadence with hard foot strikes (walking is ~100–120 steps/min at ~1.2–1.4 g)
export const RUN_WINDOW_MS = 8000;
export const RUN_MIN_CADENCE = 150; // steps per minute
export const RUN_MIN_PEAK_G = 1.6;
export const RUN_MIN_SPEED_MPS = 2.2; // ~8 km/h, checked only when a recent GPS speed is known
const SPEED_FRESH_MS = 6000;

const median = (arr) => {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
};

/**
 * createMotionDetector({ onShake, onRun }) -> { push({x,y,z}, t), pushSpeed(mps, t), reset(), stats() }
 * Callbacks receive a short human-readable reason.
 */
export const createMotionDetector = ({ onShake, onRun } = {}) => {
  let jolts = [];
  let lastJolt = 0;
  let steps = []; // { t, peak }
  let armed = true;
  let currentPeak = 0;
  let lastStep = 0;
  let speed = null; // { mps, t }
  let started = null;

  const reset = () => {
    jolts = [];
    steps = [];
    armed = true;
    currentPeak = 0;
    started = null;
  };

  const cadence = (now) => {
    const recent = steps.filter((s) => now - s.t <= RUN_WINDOW_MS);
    return { count: recent.length, perMin: (recent.length * 60000) / RUN_WINDOW_MS, peak: median(recent.map((s) => s.peak)) };
  };

  const push = ({ x, y, z }, t = Date.now()) => {
    if (started === null) started = t;
    const g = Math.sqrt(x * x + y * y + z * z);

    // --- shake
    if (onShake && g >= SHAKE_G && t - lastJolt >= JOLT_GAP_MS) {
      lastJolt = t;
      jolts = jolts.filter((j) => t - j <= SHAKE_WINDOW_MS);
      jolts.push(t);
      if (jolts.length >= SHAKE_JOLTS) {
        jolts = [];
        onShake('Phone shaken hard');
        return;
      }
    }

    // --- steps (peak detection with hysteresis)
    if (armed) {
      if (g >= STEP_HIGH_G) {
        armed = false;
        currentPeak = g;
      }
    } else if (g > currentPeak) {
      currentPeak = g;
    } else if (g <= STEP_LOW_G) {
      armed = true;
      if (t - lastStep >= STEP_MIN_GAP_MS) {
        lastStep = t;
        steps.push({ t, peak: currentPeak });
        steps = steps.filter((s) => t - s.t <= RUN_WINDOW_MS);
      }
    }

    // --- running
    if (onRun && t - started >= RUN_WINDOW_MS) {
      const c = cadence(t);
      const speedKnown = speed && t - speed.t <= SPEED_FRESH_MS;
      const fastEnough = !speedKnown || speed.mps >= RUN_MIN_SPEED_MPS;
      if (c.perMin >= RUN_MIN_CADENCE && c.peak >= RUN_MIN_PEAK_G && fastEnough) {
        steps = [];
        started = t; // need a fresh full window before firing again
        const kmh = speedKnown ? ` at ${Math.round(speed.mps * 3.6)} km/h` : '';
        onRun(`Sudden running detected (${Math.round(c.perMin)} steps/min${kmh})`);
      }
    }
  };

  const pushSpeed = (mps, t = Date.now()) => {
    if (typeof mps === 'number' && mps >= 0) speed = { mps, t };
  };

  const stats = (t = Date.now()) => {
    const c = cadence(t);
    return {
      stepsPerMin: Math.round(c.perMin),
      speedKmh: speed && t - speed.t <= SPEED_FRESH_MS ? Math.round(speed.mps * 3.6) : null,
    };
  };

  return { push, pushSpeed, reset, stats };
};
