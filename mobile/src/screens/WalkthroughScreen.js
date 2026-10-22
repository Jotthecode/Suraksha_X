// Short app tour: shown once after the first sign-in on this device, and on demand from the menu / Settings.
import React, { useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { MaterialIcons } from '@expo/vector-icons';
import { Button } from '../components/ui';
import { colors, spacing, fontSize, touchTarget } from '../theme/colors';

export const WALKTHROUGH_KEY = 'surakshax_walkthrough_done';

const SLIDES = [
  {
    icon: 'sos',
    title: 'One-tap SOS',
    text: 'Tap SOS and you get 10 seconds to cancel. Then your contacts get your location.',
  },
  {
    icon: 'record-voice-over',
    title: 'Voice SOS',
    text: 'Turn on voice SOS and saying "Bachao" or "Help" starts an alert.',
  },
  {
    icon: 'share-location',
    title: 'Live location',
    text: 'Share a link your guardians can open in any browser to follow you live.',
  },
  {
    icon: 'alt-route',
    title: 'Safe route',
    text: 'Compare the safest route with the shortest one before you set off.',
  },
  {
    icon: 'local-police',
    title: 'Contacts & police',
    text: 'Keep your emergency contacts up to date and find the nearest police station.',
  },
];

export const WalkthroughScreen = ({ navigation, route }) => {
  const replay = !!route?.params?.replay;
  const insets = useSafeAreaInsets();
  const scrollRef = useRef(null);
  const [width, setWidth] = useState(0);
  const [index, setIndex] = useState(0);
  const isLast = index === SLIDES.length - 1;

  const finish = async () => {
    try {
      await AsyncStorage.setItem(WALKTHROUGH_KEY, '1');
    } catch (e) {
      // Not fatal: worst case the tour shows again next time
    }
    if (replay && navigation.canGoBack()) navigation.goBack();
    else navigation.replace('MainTabs');
  };

  const goTo = (i) => {
    setIndex(i);
    scrollRef.current?.scrollTo({ x: i * width, animated: true });
  };

  const onScroll = (e) => {
    if (!width) return;
    const i = Math.round(e.nativeEvent.contentOffset.x / width);
    // No comparison with `index` here: this closure can be stale mid-animation; React skips same-value updates
    setIndex(Math.max(0, Math.min(SLIDES.length - 1, i)));
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <StatusBar style="dark" />
      <View style={styles.topBar}>
        <Text style={styles.brand}>SurakshaX</Text>
      </View>

      <View style={styles.flex} onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
        {width > 0 ? (
          <ScrollView
            ref={scrollRef}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onScroll={onScroll}
            scrollEventThrottle={16}
            style={styles.flex}
          >
            {SLIDES.map((s) => (
              <View key={s.title} style={[styles.slide, { width }]}>
                <View style={styles.iconCircle}>
                  <MaterialIcons name={s.icon} size={72} color={colors.primary} />
                </View>
                <Text style={styles.title}>{s.title}</Text>
                <Text style={styles.text}>{s.text}</Text>
              </View>
            ))}
          </ScrollView>
        ) : null}
      </View>

      <View style={styles.dots}>
        {SLIDES.map((s, i) => (
          <Pressable key={s.title} onPress={() => goTo(i)} hitSlop={6} accessibilityLabel={`Slide ${i + 1}`}>
            <View style={[styles.dot, i === index && styles.dotOn]} />
          </Pressable>
        ))}
      </View>

      <View style={styles.bottomBar}>
        <Pressable onPress={finish} disabled={isLast} style={styles.skipBtn} hitSlop={8} accessibilityRole="button">
          <Text style={styles.skipText}>{isLast ? '' : 'Skip'}</Text>
        </Pressable>
        <Button
          title={isLast ? (replay ? 'Done' : 'Get started') : 'Next'}
          onPress={() => (isLast ? finish() : goTo(index + 1))}
          style={styles.nextBtn}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.cardBg },
  flex: { flex: 1 },
  topBar: { height: 56, justifyContent: 'center', paddingHorizontal: spacing.screen },
  brand: { fontSize: fontSize.section, fontWeight: '700', color: colors.primary },
  slide: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.xl },
  iconCircle: {
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
  },
  title: { fontSize: 24, fontWeight: '700', color: colors.textPrimary, textAlign: 'center', marginBottom: 12 },
  text: { fontSize: 16, lineHeight: 24, color: colors.textSecondary, textAlign: 'center', maxWidth: 360 },
  dots: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: spacing.md },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.border, marginHorizontal: 4 },
  dotOn: { width: 24, backgroundColor: colors.primary },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.screen,
    paddingBottom: spacing.md,
  },
  skipBtn: { minHeight: touchTarget, minWidth: 64, justifyContent: 'center' },
  skipText: { fontSize: fontSize.body, fontWeight: '600', color: colors.textSecondary },
  nextBtn: { minWidth: 140 },
});
