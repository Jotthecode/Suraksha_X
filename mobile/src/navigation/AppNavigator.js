import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useSafety } from '../context/SafetyContext';
import { colors } from '../theme/colors';
import { navigationRef } from './navigationRef';
import { SideMenuProvider } from '../components/SideMenu';
import { DashboardScreen } from '../screens/DashboardScreen';
import { SafeRouteScreen } from '../screens/SafeRouteScreen';
import { LiveTrackingScreen } from '../screens/LiveTrackingScreen';
import { ContactsScreen } from '../screens/ContactsScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { AlertsScreen } from '../screens/AlertsScreen';
import { PoliceStationsScreen } from '../screens/PoliceStationsScreen';
import { SafetyHistoryScreen } from '../screens/SafetyHistoryScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { RecordingsScreen } from '../screens/RecordingsScreen';
import { TestingToolsScreen } from '../screens/TestingToolsScreen';
import { SafetyTriggersScreen } from '../screens/SafetyTriggersScreen';
import { WalkthroughScreen, WALKTHROUGH_KEY } from '../screens/WalkthroughScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const tabIcon = (name) => ({ color, size }) => <MaterialIcons name={name} size={size ?? 24} color={color} />;

const MainTabNavigator = () => {
  const insets = useSafeAreaInsets();
  return (
  <Tab.Navigator
    backBehavior="initialRoute"
    screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.primary,
      tabBarInactiveTintColor: colors.textSecondary,
      tabBarHideOnKeyboard: true,
      // Explicit height so icon + label always fit; bottom inset keeps it above the Android nav bar
      tabBarStyle: [styles.tabBar, { height: 64 + insets.bottom, paddingBottom: insets.bottom }],
      tabBarLabelStyle: styles.tabLabel,
    }}
  >
    <Tab.Screen
      name="DashboardTab"
      component={DashboardScreen}
      options={{ title: 'Home', tabBarIcon: tabIcon('home') }}
    />
    <Tab.Screen
      name="SafeRouteTab"
      component={SafeRouteScreen}
      options={{ title: 'Route', tabBarIcon: tabIcon('alt-route') }}
    />
    <Tab.Screen
      name="LiveTrackingTab"
      component={LiveTrackingScreen}
      options={{ title: 'Live location', tabBarIcon: tabIcon('share-location') }}
    />
    <Tab.Screen
      name="GuardiansTab"
      component={ContactsScreen}
      options={{ title: 'Contacts', tabBarIcon: tabIcon('contacts') }}
    />
  </Tab.Navigator>
  );
};

export const AppNavigator = () => {
  const { isAuthLoaded, isLoggedIn } = useSafety();
  // null = not read yet. Re-read on every login/logout so the first sign-in on this device opens the tour.
  const [tourDone, setTourDone] = useState(null);

  useEffect(() => {
    let alive = true;
    AsyncStorage.getItem(WALKTHROUGH_KEY)
      .then((v) => alive && setTourDone(v === '1'))
      .catch(() => alive && setTourDone(true));
    return () => {
      alive = false;
    };
  }, [isLoggedIn]);

  if (!isAuthLoaded || tourDone === null) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <SideMenuProvider>
        <Stack.Navigator
          // Remount on login/logout so initialRouteName (tour vs. home) is applied without flashing Home
          key={isLoggedIn ? 'app' : 'auth'}
          initialRouteName={isLoggedIn ? (tourDone ? 'MainTabs' : 'Walkthrough') : 'Login'}
          screenOptions={{
            headerShown: false,
            animation: 'slide_from_right',
            contentStyle: { backgroundColor: colors.bg },
          }}
        >
          {!isLoggedIn ? (
            <>
              <Stack.Screen name="Login" component={LoginScreen} />
              <Stack.Screen name="Register" component={RegisterScreen} />
            </>
          ) : (
            <>
              <Stack.Screen name="MainTabs" component={MainTabNavigator} />
              <Stack.Screen name="Walkthrough" component={WalkthroughScreen} options={{ animation: 'fade' }} />
              <Stack.Screen
                name="AlertsModal"
                component={AlertsScreen}
                options={{ presentation: 'fullScreenModal', animation: 'slide_from_bottom' }}
              />
              <Stack.Screen name="PoliceStations" component={PoliceStationsScreen} />
              <Stack.Screen name="SafetyHistory" component={SafetyHistoryScreen} />
              <Stack.Screen name="Recordings" component={RecordingsScreen} />
              <Stack.Screen name="Settings" component={ProfileScreen} />
              <Stack.Screen name="TestingTools" component={TestingToolsScreen} />
              <Stack.Screen name="SafetyTriggers" component={SafetyTriggersScreen} />
            </>
          )}
        </Stack.Navigator>
      </SideMenuProvider>
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg,
  },
  tabBar: {
    backgroundColor: colors.cardBg,
    borderTopColor: colors.border,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
});
