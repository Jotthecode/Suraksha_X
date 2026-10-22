import { Linking, PermissionsAndroid, Platform } from 'react-native';
import { requireOptionalNativeModule } from 'expo';

// Null on web / iOS / Expo Go, where the native module is not compiled in.
const Native = Platform.OS === 'android' ? requireOptionalNativeModule('SurakshaxNative') : null;

export const isNativeAvailable = () => !!Native;

export async function requestEmergencyPermissions() {
  if (Platform.OS !== 'android') return { sms: false, call: false };
  try {
    const res = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.SEND_SMS,
      PermissionsAndroid.PERMISSIONS.CALL_PHONE,
    ]);
    return {
      sms: res[PermissionsAndroid.PERMISSIONS.SEND_SMS] === PermissionsAndroid.RESULTS.GRANTED,
      call: res[PermissionsAndroid.PERMISSIONS.CALL_PHONE] === PermissionsAndroid.RESULTS.GRANTED,
    };
  } catch (e) {
    return { sms: false, call: false };
  }
}

/** Android 13+ asks before an app may show notifications (needed for the protection / SOS notifications). */
export async function requestNotificationPermission() {
  if (Platform.OS !== 'android' || Platform.Version < 33) return true;
  try {
    const res = await PermissionsAndroid.request('android.permission.POST_NOTIFICATIONS');
    return res === PermissionsAndroid.RESULTS.GRANTED;
  } catch (e) {
    return false;
  }
}

/**
 * Sends the SMS straight from the SIM. Falls back to opening the SMS composer
 * (user taps send) when the native module or permission is unavailable.
 */
export async function sendEmergencySms(phones, message) {
  const recipients = (phones || []).map((p) => String(p).trim()).filter(Boolean);
  if (recipients.length === 0) return [];

  if (Native && Native.canSendSms()) {
    return await Native.sendSmsAsync(recipients, message);
  }

  const sep = Platform.OS === 'ios' ? '&' : '?';
  const url = `sms:${recipients.join(',')}${sep}body=${encodeURIComponent(message)}`;
  try {
    await Linking.openURL(url);
    return recipients.map((phone) => ({ phone, status: 'composer_opened' }));
  } catch (e) {
    return recipients.map((phone) => ({ phone, status: 'failed', error: e.message }));
  }
}

export async function callNumber(phone) {
  if (Native) {
    try {
      return await Native.callAsync(String(phone));
    } catch (e) {}
  }
  await Linking.openURL(`tel:${phone}`);
  return 'dialer_opened';
}

/** Calls without a tap when Phone permission is granted; otherwise opens the dialer. */
export async function placeEmergencyCall(phone) {
  if (Native) {
    try {
      const status = await Native.placeCallAsync(String(phone));
      if (status === 'calling') return status;
    } catch (e) {}
  }
  await Linking.openURL(`tel:${phone}`).catch(() => {});
  return 'dialer_opened';
}

export const getPermissionStatus = () => (Native ? Native.permissionStatus() : null);
export const openAppSettings = () => (Native ? Native.openAppSettings() : Linking.openSettings());
export const openBatterySettings = () => (Native ? Native.openBatterySettings() : Linking.openSettings());

// Background protection (foreground service + notification)
export const startProtection = (title, text, { mic = false, location = true } = {}) =>
  Native ? Native.startProtection(title, text, mic, location) : false;
export const stopProtection = () => Native && Native.stopProtection();
export const isProtectionRunning = () => (Native ? Native.isProtectionRunning() : false);

// Native SOS countdown (keeps running in the background)
export const supportsNativeCountdown = () => !!Native;
export const startSosCountdown = (seconds, reason) => Native && Native.startSosCountdown(seconds, reason);
export const cancelSosCountdown = (notify = false) => Native && Native.cancelSosCountdown(notify);
export const getSosCountdown = () => (Native ? Native.getSosCountdown() : { running: false });
export const addSosCountdownListener = (event, fn) =>
  Native ? Native.addListener(event, fn) : { remove() {} };
