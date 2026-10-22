import * as Location from 'expo-location';

// Once the user declines the system "turn on location accuracy" dialog we stop asking:
// in an emergency a dialog every 5 seconds would block the screen.
let settingsDeclined = false;
// Only one high-accuracy request at a time, so concurrent callers can't stack dialogs.
let inFlight = null;

const withTimeout = (promise, ms) =>
  Promise.race([promise, new Promise((resolve) => setTimeout(() => resolve(null), ms))]);

const requestFix = () => {
  if (!inFlight) {
    inFlight = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High })
      .catch((e) => {
        // Recorded even if the caller already gave up waiting
        if (e && e.code === 'ERR_LOCATION_SETTINGS_UNSATISFIED') settingsDeclined = true;
        return null;
      })
      .finally(() => {
        inFlight = null;
      });
  }
  return inFlight;
};

/**
 * Best-effort current position that never blocks for long and asks the user to
 * enable location settings at most once. Returns a LocationObject or null.
 */
export const getLocationQuietly = async ({ timeoutMs = 5000, requestPermission = false } = {}) => {
  try {
    const perm = requestPermission
      ? await Location.requestForegroundPermissionsAsync()
      : await Location.getForegroundPermissionsAsync();
    if (perm.status !== 'granted') return null;

    const servicesOn = await Location.hasServicesEnabledAsync().catch(() => true);
    if (servicesOn && !settingsDeclined) {
      const fix = await withTimeout(requestFix(), timeoutMs);
      if (fix) return fix;
    }
    return await withTimeout(Location.getLastKnownPositionAsync(), 2000);
  } catch (e) {
    return null;
  }
};
