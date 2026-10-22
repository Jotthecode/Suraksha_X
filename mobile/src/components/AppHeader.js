import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { colors, fontSize } from '../theme/colors';

const HeaderIconButton = ({ icon, onPress, accessibilityLabel }) => (
  <Pressable
    onPress={onPress}
    accessibilityRole="button"
    accessibilityLabel={accessibilityLabel}
    hitSlop={4}
    android_ripple={{ color: 'rgba(255,255,255,0.25)', borderless: true, radius: 22 }}
    style={({ pressed }) => [styles.iconBtn, pressed && styles.iconBtnPressed]}
  >
    <MaterialIcons name={icon} size={24} color={colors.textLight} />
  </Pressable>
);

/**
 * Material-style top app bar.
 * leftIcon: 'back' (default) | 'menu' | 'close' | null
 * actions: [{ icon, onPress, label }]
 */
export const AppHeader = ({ title, leftIcon = 'back', onLeftPress, actions = [] }) => {
  const insets = useSafeAreaInsets();
  const iconName =
    leftIcon === 'menu' ? 'menu' : leftIcon === 'close' ? 'close' : leftIcon === 'back' ? 'arrow-back' : null;

  return (
    <View style={[styles.wrapper, { paddingTop: insets.top }]}>
      <View style={styles.bar}>
        {iconName ? (
          <HeaderIconButton
            icon={iconName}
            onPress={onLeftPress}
            accessibilityLabel={leftIcon === 'menu' ? 'Open menu' : leftIcon === 'close' ? 'Close' : 'Go back'}
          />
        ) : (
          <View style={styles.leftSpacer} />
        )}
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        <View style={styles.actions}>
          {actions.map((a) => (
            <HeaderIconButton key={a.icon} icon={a.icon} onPress={a.onPress} accessibilityLabel={a.label} />
          ))}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: colors.primary,
    elevation: 4,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 3,
    zIndex: 10,
  },
  bar: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  iconBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconBtnPressed: {
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  leftSpacer: {
    width: 12,
  },
  title: {
    flex: 1,
    marginLeft: 12,
    fontSize: fontSize.title,
    fontWeight: '600',
    color: colors.textLight,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
