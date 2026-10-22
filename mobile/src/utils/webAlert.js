import { Alert, Platform } from 'react-native';

/**
 * react-native-web's Alert.alert is a no-op, so confirm dialogs (log out, delete contact, …)
 * silently do nothing in the browser. On web, map it to the browser's own dialogs:
 *  - 0–1 buttons: window.alert, then run that button's onPress
 *  - 2+ buttons: window.confirm; OK runs the last non-cancel button, Cancel runs the cancel button
 * Android and iOS keep the native Alert.
 */
if (Platform.OS === 'web' && typeof window !== 'undefined') {
  Alert.alert = (title, message, buttons) => {
    const text = [title, message].filter(Boolean).join('\n\n');
    if (!buttons || buttons.length <= 1) {
      window.alert(text);
      buttons?.[0]?.onPress?.();
      return;
    }
    const cancel = buttons.find((b) => b.style === 'cancel');
    const confirm = [...buttons].reverse().find((b) => b.style !== 'cancel') || buttons[buttons.length - 1];
    if (window.confirm(text)) confirm?.onPress?.();
    else cancel?.onPress?.();
  };
}
