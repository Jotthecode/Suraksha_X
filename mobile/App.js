import React from 'react';
import { StyleSheet, View, Platform, StatusBar as RNStatusBar } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { SafetyProvider } from './src/context/SafetyContext';
import { TriggerProvider } from './src/context/TriggerContext';
import { AppNavigator } from './src/navigation/AppNavigator';

export default function App() {
  if (Platform.OS === 'web') {
    return (
      <SafeAreaProvider>
        <SafetyProvider>
          <StatusBar style="light" backgroundColor="#B71C1C" />
          <View style={styles.webContainer}>
            {/* Centered Samsung One UI Phone Shell for Desktop Browsers */}
            <View style={styles.phoneFrame}>
              {/* Phone Status Bar Accent */}
              <View style={styles.phoneStatusBar}>
                <View style={styles.phoneSpeaker} />
              </View>

              {/* Real Expo Navigation & Screens */}
              <View style={styles.phoneScreenContent}>
                <TriggerProvider>
                  <AppNavigator />
                </TriggerProvider>
              </View>
            </View>
          </View>
        </SafetyProvider>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <SafetyProvider>
        <StatusBar style="light" backgroundColor="#B71C1C" />
        <TriggerProvider>
          <AppNavigator />
        </TriggerProvider>
      </SafetyProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  webContainer: {
    flex: 1,
    width: '100%',
    minHeight: '100vh',
    backgroundColor: '#1E293B', // Sleek slate dark desktop backdrop like web_ui.py
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
    paddingHorizontal: 8,
  },
  phoneFrame: {
    width: '100%',
    maxWidth: 425,
    height: '95vh',
    maxHeight: 890,
    backgroundColor: '#F3F5F9',
    borderRadius: 36,
    overflow: 'hidden',
    borderWidth: 8,
    borderColor: '#0F172A',
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 25 },
    shadowOpacity: 0.65,
    shadowRadius: 50,
    elevation: 20,
    display: 'flex',
    flexDirection: 'column',
  },
  phoneStatusBar: {
    height: 18,
    backgroundColor: '#B71C1C',
    alignItems: 'center',
    justifyContent: 'center',
  },
  phoneSpeaker: {
    width: 48,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.4)',
  },
  phoneScreenContent: {
    flex: 1,
    backgroundColor: '#F3F5F9',
  },
});
