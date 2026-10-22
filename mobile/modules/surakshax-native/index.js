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
