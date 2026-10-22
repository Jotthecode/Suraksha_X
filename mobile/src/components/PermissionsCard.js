import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Alert, AppState, PermissionsAndroid, Platform } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Card } from './ui';
import { getPermissionStatus, openAppSettings, openBatterySettings } from '../../modules/surakshax-native';
import { colors, spacing, fontSize, touchTarget } from '../theme/colors';

const P = PermissionsAndroid.PERMISSIONS;

const ROWS = [
  { key: 'sms', icon: 'sms', label: 'Send SMS automatically', permission: P.SEND_SMS, restricted: true },
  { key: 'call', icon: 'call', label: 'Call automatically', permission: P.CALL_PHONE, restricted: true },
  { key: 'microphone', icon: 'mic', label: 'Microphone', permission: P.RECORD_AUDIO },
  { key: 'location', icon: 'location-on', label: 'Location', permission: P.ACCESS_FINE_LOCATION },
  { key: 'notifications', icon: 'notifications', label: 'Notifications', permission: 'android.permission.POST_NOTIFICATIONS' },
  { key: 'batteryUnrestricted', icon: 'battery-charging-full', label: 'Battery: unrestricted', battery: true },
];

// Android 13+ silently blocks SMS / Phone permission for apps installed from an APK file
const explainRestricted = (label) =>
  Alert.alert(
    `Allow "${label}"`,
    'Android blocks this for apps installed from an APK file. On the next screen:\n\n' +
      '1. Tap ⋮ (top right) → "Allow restricted settings" and confirm.\n' +
      '2. Go back to Permissions → SMS (and Phone) → Allow.\n\n' +
      'If you don\'t see "Allow restricted settings", just open Permissions and allow SMS and Phone.',
    [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Open settings', onPress: () => openAppSettings() },
    ]
  );

/** Shows which Android permissions SOS needs and gets the user to the right switch. Android only. */
export const PermissionsCard = ({ style }) => {
  const [status, setStatus] = useState(null);

  const refresh = useCallback(() => setStatus(getPermissionStatus()), []);

  useEffect(() => {
    refresh();
    // Re-check when the user comes back from the system settings screen
    const sub = AppState.addEventListener('change', (s) => s === 'active' && refresh());
    return () => sub.remove();
  }, [refresh]);

  if (Platform.OS !== 'android' || !status) return null;

  const fix = async (row) => {
    if (row.battery) {
      openBatterySettings();
      return;
    }
    if (row.key === 'notifications' && Platform.Version < 33) {
      openAppSettings();
      return;
    }
    let result;
    try {
      result = await PermissionsAndroid.request(row.permission);
    } catch (e) {
      result = 'error';
    }
    refresh();
    if (result === PermissionsAndroid.RESULTS.GRANTED) return;
    if (row.restricted && Platform.Version >= 33) explainRestricted(row.label);
    else openAppSettings();
  };

  const rows = ROWS.filter((r) => (r.key === 'sms' || r.key === 'call' ? status.hasTelephony : true));
  const missing = rows.filter((r) => !status[r.key]).length;

  return (
    <Card padded={false} style={style}>
      <View style={styles.header}>
        <MaterialIcons
          name={missing ? 'error-outline' : 'verified-user'}
          size={22}
          color={missing ? colors.warning : colors.safe}
        />
        <Text style={styles.headerText}>
          {missing ? `${missing} permission${missing > 1 ? 's' : ''} missing` : 'All set for automatic SOS'}
        </Text>
      </View>
      {rows.map((row) => {
        const ok = !!status[row.key];
        return (
          <View key={row.key} style={styles.row}>
            <MaterialIcons name={row.icon} size={20} color={colors.textSecondary} />
            <Text style={styles.label}>{row.label}</Text>
            {ok ? (
              <MaterialIcons name="check-circle" size={22} color={colors.safe} accessibilityLabel="Allowed" />
            ) : (
              <Pressable onPress={() => fix(row)} style={styles.fixBtn} hitSlop={6} accessibilityRole="button">
                <Text style={styles.fixText}>{row.battery ? 'Change' : 'Allow'}</Text>
              </Pressable>
            )}
          </View>
        );
      })}
    </Card>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  headerText: { fontSize: fontSize.body, fontWeight: '700', color: colors.textPrimary },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: touchTarget,
    paddingHorizontal: spacing.md,
  },
  label: { flex: 1, fontSize: fontSize.body, color: colors.textPrimary },
  fixBtn: {
    paddingHorizontal: spacing.md,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fixText: { color: colors.textLight, fontWeight: '700', fontSize: fontSize.caption },
});
