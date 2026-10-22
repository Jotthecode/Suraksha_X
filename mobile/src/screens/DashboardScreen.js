import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Linking,
  ActivityIndicator,
  Alert,
  Switch,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafety } from '../context/SafetyContext';
import { colors, spacing, radius, fontSize } from '../theme/colors';
import { PulsingSOSButton } from '../components/PulsingSOSButton';
import { Screen, Card, SectionTitle, Chip } from '../components/ui';
import { useSideMenu } from '../components/SideMenu';
import { useTriggers } from '../context/TriggerContext';

const QUICK_ACTIONS = [
  { key: 'route', icon: 'alt-route', label: 'Safe route', target: 'SafeRouteTab' },
  { key: 'live', icon: 'share-location', label: 'Live location', target: 'LiveTrackingTab' },
  { key: 'contacts', icon: 'contacts', label: 'Contacts', target: 'GuardiansTab' },
  { key: 'recordings', icon: 'mic', label: 'Recordings', target: 'Recordings' },
  { key: 'history', icon: 'history', label: 'SOS history', target: 'SafetyHistory' },
  { key: 'police', icon: 'local-police', label: 'Nearby police', target: 'PoliceStations' },
];

const riskTone = (category) => {
  const c = (category || '').toLowerCase();
  if (c.includes('high')) return 'danger';
  if (c.includes('medium')) return 'warning';
  if (c.includes('low') || c.includes('safe')) return 'safe';
  return 'default';
};

const dial = (number) => {
  // Opens the dialer only: the user still presses call, so a stray tap never auto-dials
  Linking.openURL(`tel:${number}`).catch(() => Alert.alert('Cannot open dialer', `Please dial ${number} manually.`));
};

export const DashboardScreen = ({ navigation }) => {
  const { guardians, currentLocation, riskData, isRefreshingLocation, detectDeviceLocation } = useSafety();
  const { openMenu } = useSideMenu();

  const { settings, updateSettings, voiceStatus, voiceState, motionState } = useTriggers();
  const motionError = (settings.shakeEnabled || settings.runEnabled) && motionState.error;

  const primaryGuardian = guardians[0];
  const address =
    currentLocation.address ||
    `${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}`;
  const riskLabel = riskData?.category || 'Checking…';
  const riskPct = riskData?.risk_score ? ` ${(riskData.risk_score * 100).toFixed(0)}%` : '';

  return (
    <Screen
      title="SurakshaX"
      leftIcon="menu"
      onLeftPress={openMenu}
      actions={[{ icon: 'account-circle', label: 'Settings', onPress: () => navigation.navigate('Settings') }]}
    >
      {/* Location + area safety */}
      <Card style={styles.locationCard}>
        <MaterialIcons name="place" size={22} color={colors.primary} />
        <View style={styles.locationTextBox}>
          <Text style={styles.locationAddress} numberOfLines={2}>
            {address}
          </Text>
          <View style={styles.riskRow}>
            <Text style={styles.caption}>Area safety</Text>
            <Chip label={`${riskLabel}${riskPct}`} tone={riskTone(riskLabel)} />
          </View>
        </View>
        <Pressable
          onPress={detectDeviceLocation}
          disabled={isRefreshingLocation}
          accessibilityLabel="Refresh location"
          android_ripple={{ color: colors.divider, borderless: true, radius: 24 }}
          style={styles.refreshBtn}
        >
          {isRefreshingLocation ? (
            <ActivityIndicator size="small" color={colors.accent} />
          ) : (
            <MaterialIcons name="my-location" size={22} color={colors.accent} />
          )}
        </Pressable>
      </Card>

      {/* SOS */}
      <View style={styles.sosArea}>
        <PulsingSOSButton
          size={170}
          onPress={() => navigation.navigate('AlertsModal', { triggerReason: 'Manual Emergency SOS Panic Button' })}
        />
      </View>

      {/* Emergency numbers */}
      <SectionTitle>Emergency numbers</SectionTitle>
      <View style={styles.numbersRow}>
        <NumberButton number="112" label="Police" icon="local-police" onPress={() => dial('112')} />
        <NumberButton number="1091" label="Women helpline" icon="support-agent" onPress={() => dial('1091')} />
        {primaryGuardian ? (
          <NumberButton
            number={primaryGuardian.name || 'Contact'}
            label={primaryGuardian.phone}
            icon="call"
            onPress={() => dial(primaryGuardian.phone)}
          />
        ) : (
          <NumberButton
            number="Add"
            label="Contact"
            icon="person-add"
            onPress={() => navigation.navigate('GuardiansTab')}
          />
        )}
      </View>

      {/* Hands-free triggers */}
      <SectionTitle
        right={
          <Pressable onPress={() => navigation.navigate('SafetyTriggers')} hitSlop={8}>
            <Text style={styles.link}>Set up</Text>
          </Pressable>
        }
      >
        Hands-free SOS
      </SectionTitle>
      <Card padded={false}>
        <TriggerSwitch
          icon={settings.voiceEnabled ? 'mic' : 'mic-none'}
          label="Voice"
          value={settings.voiceEnabled}
          onChange={(v) => updateSettings({ voiceEnabled: v })}
          status={voiceStatus}
          warn={voiceState === 'error'}
        />
        <TriggerSwitch
          icon="vibration"
          label="Shake phone"
          value={settings.shakeEnabled}
          onChange={(v) => updateSettings({ shakeEnabled: v })}
          status={motionError || null}
          warn={!!motionError}
          divider
        />
        <TriggerSwitch
          icon="directions-run"
          label="Sudden running"
          value={settings.runEnabled}
          onChange={(v) => updateSettings({ runEnabled: v })}
          status={motionError || null}
          warn={!!motionError}
          divider
        />
      </Card>

      {/* Quick actions */}
      <SectionTitle>Quick actions</SectionTitle>
      <View style={styles.grid}>
        {QUICK_ACTIONS.map((a) => (
          <View key={a.key} style={styles.gridCell}>
            <Pressable
              onPress={() => navigation.navigate(a.target)}
              android_ripple={{ color: colors.divider }}
              style={({ pressed }) => [styles.gridItem, pressed && { opacity: 0.85 }]}
            >
              <View style={styles.gridIcon}>
                <MaterialIcons name={a.icon} size={24} color={colors.primary} />
              </View>
              <Text style={styles.gridLabel} numberOfLines={1}>
                {a.label}
              </Text>
            </Pressable>
          </View>
        ))}
      </View>
    </Screen>
  );
};

const NumberButton = ({ number, label, icon, onPress }) => (
  <Pressable
    onPress={onPress}
    android_ripple={{ color: colors.divider }}
    style={({ pressed }) => [styles.numberBtn, pressed && { opacity: 0.85 }]}
  >
    <MaterialIcons name={icon} size={22} color={colors.primary} />
    <Text style={styles.numberText} numberOfLines={1}>
      {number}
    </Text>
    <Text style={styles.numberLabel} numberOfLines={1}>
      {label}
    </Text>
  </Pressable>
);

const TriggerSwitch = ({ icon, label, value, onChange, status, warn, divider }) => (
  <View style={divider && styles.rowDivider}>
    <View style={styles.switchRow}>
      <MaterialIcons name={icon} size={22} color={value ? colors.primary : colors.textSecondary} />
      <Text style={styles.switchLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false: colors.border, true: colors.highRiskBorder }}
        thumbColor={value ? colors.primary : '#F4F4F5'}
        accessibilityLabel={label}
      />
    </View>
    {value && status ? (
      <Text style={[styles.voiceStatus, warn && { color: colors.warning }]} numberOfLines={2}>
        {status}
      </Text>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  locationCard: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  locationTextBox: {
    flex: 1,
    marginHorizontal: 12,
  },
  locationAddress: {
    fontSize: fontSize.body,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  riskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  caption: {
    fontSize: fontSize.caption,
    color: colors.textSecondary,
  },
  refreshBtn: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosArea: {
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  numbersRow: {
    flexDirection: 'row',
    marginHorizontal: -spacing.xs,
    marginBottom: spacing.md,
  },
  numberBtn: {
    flex: 1,
    minHeight: 80,
    marginHorizontal: spacing.xs,
    backgroundColor: colors.cardBg,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xs,
    paddingVertical: spacing.sm,
    elevation: 1,
    overflow: 'hidden',
  },
  numberText: {
    fontSize: fontSize.section,
    fontWeight: '700',
    color: colors.textPrimary,
    marginTop: spacing.xs,
  },
  numberLabel: {
    fontSize: fontSize.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  switchRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
  },
  switchLabel: {
    flex: 1,
    marginLeft: spacing.md,
    fontSize: fontSize.body,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  rowDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.divider },
  link: { color: colors.accent, fontSize: fontSize.body, fontWeight: '600' },
  voiceStatus: {
    fontSize: fontSize.caption,
    color: colors.textSecondary,
    paddingHorizontal: spacing.md,
    paddingBottom: 12,
    marginLeft: 38,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -spacing.xs,
  },
  gridCell: {
    width: '33.333%',
    padding: spacing.xs,
  },
  gridItem: {
    height: 96,
    backgroundColor: colors.cardBg,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xs,
    elevation: 1,
    overflow: 'hidden',
  },
  gridIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  gridLabel: {
    fontSize: fontSize.caption,
    fontWeight: '500',
    color: colors.textPrimary,
  },
});
