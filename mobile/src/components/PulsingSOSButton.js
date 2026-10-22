import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated, Easing } from 'react-native';
import * as Haptics from 'expo-haptics';
import { MaterialIcons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

export const PulsingSOSButton = ({ onPress, size = 180, label = 'Tap for help' }) => {
  const pulseAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Infinite pulsating wave animation
    const loop = Animated.loop(
      Animated.timing(pulseAnim, {
        toValue: 1,
        duration: 2000,
        easing: Easing.out(Easing.ease),
        useNativeDriver: true,
      })
    );
    loop.start();
    return () => loop.stop();
  }, [pulseAnim]);

  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.94,
      useNativeDriver: true,
    }).start();
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    } catch (e) {}
  };

  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      friction: 4,
      tension: 40,
      useNativeDriver: true,
    }).start();
  };

  const handlePress = () => {
    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    } catch (e) {}
    if (onPress) onPress();
  };

  // Outer ripple interpolation
  const rippleScale = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.45],
  });

  const rippleOpacity = pulseAnim.interpolate({
    inputRange: [0, 0.6, 1],
    outputRange: [0.55, 0.25, 0],
  });

  const innerRippleScale = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.25],
  });

  const innerRippleOpacity = pulseAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.4, 0.15, 0],
  });

  return (
    <View style={[styles.wrapper, { height: size * 1.5, width: size * 1.5 }]}>
      {/* Outer Glow Pulse */}
      <Animated.View
        style={[
          styles.pulseRing,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            transform: [{ scale: rippleScale }],
            opacity: rippleOpacity,
          },
        ]}
      />

      {/* Mid Glow Pulse */}
      <Animated.View
        style={[
          styles.pulseRingInner,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            transform: [{ scale: innerRippleScale }],
            opacity: innerRippleOpacity,
          },
        ]}
      />

      {/* Main Touch Button */}
      <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
        <TouchableOpacity
          activeOpacity={0.88}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          onPress={handlePress}
          style={[
            styles.sosButton,
            {
              width: size,
              height: size,
              borderRadius: size / 2,
            },
          ]}
        >
          <View style={styles.innerContent}>
            <MaterialIcons name="notifications-active" size={28} color="#FFFFFF" />
            <Text style={styles.sosText}>SOS</Text>
            <Text style={styles.subText}>{label}</Text>
          </View>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginVertical: 4,
  },
  pulseRing: {
    position: 'absolute',
    backgroundColor: colors.sosRedPulse,
    borderWidth: 2,
    borderColor: colors.sosRed,
  },
  pulseRingInner: {
    position: 'absolute',
    backgroundColor: 'rgba(220, 38, 38, 0.18)',
  },
  sosButton: {
    backgroundColor: colors.sosRed,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.sosRed,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.45,
    shadowRadius: 20,
    elevation: 12,
    borderWidth: 5,
    borderColor: '#FFFFFF',
  },
  innerContent: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosText: {
    fontSize: 36,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 2,
    textShadowColor: 'rgba(0, 0, 0, 0.35)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  subText: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.92)',
    marginTop: 2,
  },
});
