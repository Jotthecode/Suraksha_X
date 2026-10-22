import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Alert, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useSafety } from '../context/SafetyContext';
import { AppHeader } from '../components/AppHeader';
import { ListRow } from '../components/ui';
import { colors, spacing, radius, fontSize, touchTarget } from '../theme/colors';

const dispatchSummary = (info) => {
  if (!info) return '';
  const lines = [];
  if (info.noGuardians) {
    lines.push('No emergency contacts saved, so no SMS was sent. Add contacts in the Contacts tab.');
  } else {
    const sent = (info.smsResults || []).filter((r) => r.status === 'sent').length;
    const total = (info.smsResults || []).length;
    if (sent > 0) lines.push(`SMS with your live location sent to ${sent} of ${total} contacts.`);
    else if ((info.smsResults || []).some((r) => r.status === 'composer_opened')) lines.push('SMS app opened – press Send to alert your contacts.');
    else lines.push('SMS could not be sent from this phone. Call 112 now.');
  }
  lines.push(info.offline ? 'Server unreachable – police dashboard not notified.' : 'Nearest police station notified.');
  lines.push('Your live location is shared for the next 2 hours.');
  return lines.join('\n');
};

export const AlertsScreen = ({ navigation, route }) => {
  const {
    user,
    guardians,
    currentLocation,
    executeDispatch,
  } = useSafety();

  const triggerReason = route.params?.triggerReason || 'Emergency SOS Button';

  const [secondsLeft, setSecondsLeft] = useState(10);
  const [isDispatched, setIsDispatched] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [dispatchInfo, setDispatchInfo] = useState(null);

  const pulseScale = useRef(new Animated.Value(1)).current;
  const isSafePressed = useRef(false);

  useEffect(() => {
    // Pulse animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseScale, {
          toValue: 1.15,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(pulseScale, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Countdown interval
    const interval = setInterval(() => {
      setSecondsLeft((prev) => {
        if (isSafePressed.current) return prev;
        if (prev <= 1) {
          clearInterval(interval);
          triggerAutomaticDispatch();
          return 0;
        }

        // Haptic pulse per tick
        try {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        } catch (e) {}

        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const dispatchStarted = useRef(false);

  const triggerAutomaticDispatch = async () => {
    if (isSafePressed.current || dispatchStarted.current) return;
    dispatchStarted.current = true;
    setIsSending(true);
    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    } catch (e) {}

    const res = await executeDispatch(triggerReason);
    setIsSending(false);
    setIsDispatched(true);
    setDispatchInfo(res);
  };

  const handleSafeCancel = () => {
    if (dispatchStarted.current) return;
    isSafePressed.current = true;
    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {}
    Alert.alert('SOS Cancelled', 'False alarm recorded. You are safe.', [
      { text: 'OK', onPress: () => navigation.goBack() },
    ]);
  };

  const handleInstantDispatch = () => {
    triggerAutomaticDispatch();
  };

  const insets = useSafeAreaInsets();

  const handleBack = () => {
    if (dispatchStarted.current) navigation.goBack();
    else handleSafeCancel();
  };

  return (
    <View style={styles.root}>
      <AppHeader title="Emergency SOS" onLeftPress={handleBack} />
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: spacing.md + insets.bottom }]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.center}>
          {!isDispatched ? (
            <Animated.View style={[styles.circle, { transform: [{ scale: pulseScale }] }]}>
              <Text style={styles.countNumber}>{secondsLeft}</Text>
              <Text style={styles.countLabel}>seconds</Text>
            </Animated.View>
          ) : (
            <View style={[styles.circle, styles.circleDone]}>
              <MaterialIcons name="check" size={56} color={colors.textLight} />
              <Text style={styles.countLabel}>Alert sent</Text>
            </View>
          )}

          <Text style={styles.message}>
            {!isDispatched
              ? isSending
                ? 'Sending alert…'
                : 'Your contacts and the nearest police will be alerted when the timer ends.'
              : dispatchSummary(dispatchInfo)}
          </Text>
        </View>

        <View style={styles.infoCard}>
          <ListRow icon="info-outline" label="Reason" secondary={triggerReason} />
          <ListRow
            icon="place"
            label="Location"
            secondary={`${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}`}
            divider
          />
          <ListRow
            icon="person"
            label="First contact"
            secondary={guardians[0] ? `${guardians[0].name} (${guardians[0].phone})` : 'None saved'}
            divider
          />
          <ListRow icon="local-police" label="Nearest police" secondary={dispatchInfo?.nearestPolice || 'Locating…'} divider />
        </View>

        {!isDispatched ? (
          <>
            <Pressable
              style={({ pressed }) => [styles.safeBtn, pressed && styles.pressed]}
              onPress={handleSafeCancel}
              disabled={isSending}
            >
              <MaterialIcons name="verified-user" size={22} color={colors.safe} />
              <Text style={styles.safeBtnText}>I'm safe, cancel</Text>
            </Pressable>
            <Pressable
              style={({ pressed }) => [styles.sendBtn, pressed && styles.pressed]}
              onPress={handleInstantDispatch}
              disabled={isSending}
            >
              {isSending ? (
                <ActivityIndicator size="small" color={colors.textLight} />
              ) : (
                <>
                  <MaterialIcons name="send" size={20} color={colors.textLight} />
                  <Text style={styles.sendBtnText}>Send now</Text>
                </>
              )}
            </Pressable>
          </>
        ) : (
          <Pressable style={({ pressed }) => [styles.safeBtn, pressed && styles.pressed]} onPress={() => navigation.goBack()}>
            <Text style={[styles.safeBtnText, { color: colors.textPrimary }]}>Back to home</Text>
          </Pressable>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.primaryDark },
  content: { paddingHorizontal: spacing.screen, paddingTop: spacing.lg },
  center: { alignItems: 'center' },
  circle: {
    width: 168,
    height: 168,
    borderRadius: 84,
    backgroundColor: colors.sosRed,
    borderWidth: 6,
    borderColor: 'rgba(255,255,255,0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 8,
  },
  circleDone: { backgroundColor: colors.safe },
  countNumber: { fontSize: 64, fontWeight: '800', color: colors.textLight, lineHeight: 72 },
  countLabel: { fontSize: fontSize.body, fontWeight: '600', color: colors.textLight },
  message: {
    fontSize: fontSize.body,
    lineHeight: 20,
    color: colors.primaryLight,
    textAlign: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  infoCard: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.md,
    overflow: 'hidden',
    marginBottom: spacing.md,
  },
  safeBtn: {
    minHeight: 56,
    borderRadius: radius.sm,
    backgroundColor: colors.cardBg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  safeBtnText: { marginLeft: spacing.sm, fontSize: fontSize.section, fontWeight: '700', color: colors.safe },
  sendBtn: {
    minHeight: touchTarget,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.7)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnText: { marginLeft: spacing.sm, fontSize: fontSize.body, fontWeight: '600', color: colors.textLight },
  pressed: { opacity: 0.85 },
});
