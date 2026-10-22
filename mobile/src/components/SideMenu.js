// Left navigation drawer built with React Native core only (Modal + Animated).
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Animated,
  Pressable,
  ScrollView,
  Alert,
  Easing,
  useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafety } from '../context/SafetyContext';
import { navigateTo } from '../navigation/navigationRef';
import { colors, spacing, fontSize } from '../theme/colors';
import appJson from '../../app.json';

const APP_VERSION = appJson?.expo?.version || '';

export const MENU_GROUPS = [
  {
    label: 'Safety',
    items: [
      { key: 'home', icon: 'home', label: 'Home', route: ['MainTabs', { screen: 'DashboardTab' }] },
      { key: 'route', icon: 'alt-route', label: 'Safe route', route: ['MainTabs', { screen: 'SafeRouteTab' }] },
      { key: 'live', icon: 'share-location', label: 'Share live location', route: ['MainTabs', { screen: 'LiveTrackingTab' }] },
      { key: 'police', icon: 'local-police', label: 'Nearby police', route: ['PoliceStations'] },
      { key: 'triggers', icon: 'record-voice-over', label: 'Safety triggers', route: ['SafetyTriggers'] },
    ],
  },
  {
    label: 'People',
    items: [
      { key: 'contacts', icon: 'contacts', label: 'Emergency contacts', route: ['MainTabs', { screen: 'GuardiansTab' }] },
    ],
  },
  {
    label: 'Records',
    items: [
      { key: 'history', icon: 'history', label: 'SOS history', route: ['SafetyHistory'] },
      { key: 'recordings', icon: 'mic', label: 'Recordings', route: ['Recordings'] },
    ],
  },
  {
    label: 'App',
    items: [
      { key: 'settings', icon: 'settings', label: 'Settings', route: ['Settings'] },
      { key: 'tour', icon: 'tour', label: 'App tour', route: ['Walkthrough', { replay: true }] },
      { key: 'testing', icon: 'science', label: 'Testing tools', route: ['TestingTools'] },
    ],
  },
];

const SideMenuContext = createContext({ openMenu: () => {}, closeMenu: () => {} });

export const useSideMenu = () => useContext(SideMenuContext);

export const SideMenuProvider = ({ children }) => {
  const [open, setOpen] = useState(false);
  const openMenu = useCallback(() => setOpen(true), []);
  const closeMenu = useCallback(() => setOpen(false), []);
  const value = useMemo(() => ({ openMenu, closeMenu }), [openMenu, closeMenu]);

  return (
    <SideMenuContext.Provider value={value}>
      {children}
      <SideMenu open={open} onClose={closeMenu} />
    </SideMenuContext.Provider>
  );
};

const SideMenu = ({ open, onClose }) => {
  const { user, logoutUser } = useSafety();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const drawerWidth = Math.min(320, Math.round(width * 0.82));

  const [mounted, setMounted] = useState(open);
  const progress = useRef(new Animated.Value(0)).current;
  const pendingAction = useRef(null);

  useEffect(() => {
    if (open) {
      setMounted(true);
      Animated.timing(progress, {
        toValue: 1,
        duration: 220,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }).start();
    } else if (mounted) {
      Animated.timing(progress, {
        toValue: 0,
        duration: 180,
        easing: Easing.in(Easing.cubic),
        useNativeDriver: true,
      }).start(() => {
        setMounted(false);
        const action = pendingAction.current;
        pendingAction.current = null;
        if (action) action();
      });
    }
  }, [open]);

  const go = (route) => {
    pendingAction.current = () => navigateTo(route[0], route[1]);
    onClose();
  };

  const confirmLogout = () => {
    pendingAction.current = () =>
      Alert.alert('Log out?', 'Your contacts and SOS history stay on this phone.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Log out', style: 'destructive', onPress: logoutUser },
      ]);
    onClose();
  };

  const translateX = progress.interpolate({ inputRange: [0, 1], outputRange: [-drawerWidth, 0] });
  const backdropOpacity = progress.interpolate({ inputRange: [0, 1], outputRange: [0, 0.5] });
  const initial = (user?.name || user?.email || '?').trim().charAt(0).toUpperCase();

  return (
    <Modal visible={mounted} transparent animationType="none" onRequestClose={onClose} statusBarTranslucent>
      <View style={styles.root}>
        <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close menu" />
        </Animated.View>

        <Animated.View style={[styles.drawer, { width: drawerWidth, transform: [{ translateX }] }]}>
          <View style={[styles.userBox, { paddingTop: insets.top + spacing.md }]}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initial}</Text>
            </View>
            <Text style={styles.userName} numberOfLines={1}>
              {user?.name || 'SurakshaX user'}
            </Text>
            {user?.email ? (
              <Text style={styles.userEmail} numberOfLines={1}>
                {user.email}
              </Text>
            ) : null}
          </View>

          <ScrollView style={styles.flex} contentContainerStyle={{ paddingBottom: spacing.sm }}>
            {MENU_GROUPS.map((group, gi) => (
              <View key={group.label} style={[styles.group, gi > 0 && styles.groupDivider]}>
                <Text style={styles.groupLabel}>{group.label.toUpperCase()}</Text>
                {group.items.map((item) => (
                  <Pressable
                    key={item.key}
                    onPress={() => go(item.route)}
                    android_ripple={{ color: colors.divider }}
                    style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
                  >
                    <MaterialIcons name={item.icon} size={22} color={colors.textSecondary} />
                    <Text style={styles.itemLabel}>{item.label}</Text>
                  </Pressable>
                ))}
              </View>
            ))}
          </ScrollView>

          <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.sm }]}>
            <Pressable
              onPress={confirmLogout}
              android_ripple={{ color: colors.divider }}
              style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
            >
              <MaterialIcons name="logout" size={22} color={colors.primary} />
              <Text style={[styles.itemLabel, { color: colors.primary }]}>Log out</Text>
            </Pressable>
            {APP_VERSION ? <Text style={styles.version}>Version {APP_VERSION}</Text> : null}
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  root: { flex: 1 },
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: '#000000' },
  drawer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    backgroundColor: colors.cardBg,
    elevation: 16,
    shadowColor: '#000000',
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  userBox: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.25)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  avatarText: { color: colors.textLight, fontSize: 20, fontWeight: '700' },
  userName: { color: colors.textLight, fontSize: fontSize.section, fontWeight: '600' },
  userEmail: { color: 'rgba(255,255,255,0.85)', fontSize: fontSize.body, marginTop: 2 },
  group: { paddingVertical: spacing.sm },
  groupDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  groupLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.8,
    color: colors.textMuted,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xs,
    paddingBottom: spacing.xs,
  },
  item: {
    height: 48,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
  },
  itemPressed: { backgroundColor: colors.bg },
  itemLabel: { marginLeft: 24, fontSize: fontSize.body, fontWeight: '500', color: colors.textPrimary },
  footer: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, paddingTop: spacing.xs },
  version: { fontSize: 11, color: colors.textMuted, paddingHorizontal: spacing.md, paddingTop: spacing.xs },
});
