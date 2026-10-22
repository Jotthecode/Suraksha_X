import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafety } from '../context/SafetyContext';
import { getBaseUrl, setBaseUrl, DEFAULT_HOST } from '../api/config';
import { Card, Button, TextField } from '../components/ui';
import { colors, spacing, fontSize } from '../theme/colors';

export const LoginScreen = ({ navigation }) => {
  const { user, loginUser } = useSafety();
  const [email, setEmail] = useState(user.email || '');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showServer, setShowServer] = useState(false);
  const [serverUrl, setServerUrl] = useState(DEFAULT_HOST);

  useEffect(() => {
    getBaseUrl().then(setServerUrl);
  }, []);

  const saveServer = async () => {
    const url = serverUrl.trim().replace(/\/+$/, '');
    if (!/^https?:\/\//.test(url)) {
      Alert.alert('Invalid URL', 'Server URL must start with http:// or https://');
      return;
    }
    await setBaseUrl(url);
    setServerUrl(url);
    setShowServer(false);
  };

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Missing Credentials', 'Please provide both your registered email and password.');
      return;
    }
    setIsLoading(true);
    const res = await loginUser(email, password);
    setIsLoading(false);

    if (res.success) {
    } else {
      Alert.alert('Login Error', res.error || 'Invalid email or password');
    }
  };

  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <StatusBar style="dark" />
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={[
            styles.container,
            { paddingTop: insets.top + spacing.xl, paddingBottom: insets.bottom + spacing.lg },
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.brand}>
            <View style={styles.logo}>
              <MaterialIcons name="shield" size={36} color={colors.textLight} />
            </View>
            <Text style={styles.brandTitle}>SurakshaX</Text>
          </View>

          <Card>
            <Text style={styles.cardTitle}>Sign in</Text>
            <TextField
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="you@example.com"
            />
            <TextField
              label="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
              placeholder="Password"
              returnKeyType="go"
              onSubmitEditing={handleLogin}
            />
            <Button title="Sign in" loading={isLoading} onPress={handleLogin} />

            <View style={styles.registerRow}>
              <Text style={styles.promptText}>New to SurakshaX?</Text>
              <Pressable onPress={() => navigation.navigate('Register')} hitSlop={12} style={styles.linkBtn}>
                <Text style={styles.link}>Create account</Text>
              </Pressable>
            </View>
          </Card>

          <Pressable onPress={() => setShowServer((v) => !v)} style={styles.serverToggle} hitSlop={8}>
            <MaterialIcons name="dns" size={18} color={colors.textSecondary} />
            <Text style={styles.serverToggleText}>Server settings</Text>
            <MaterialIcons name={showServer ? 'expand-less' : 'expand-more'} size={20} color={colors.textSecondary} />
          </Pressable>

          {showServer && (
            <Card>
              <TextField
                label="Server URL"
                value={serverUrl}
                onChangeText={setServerUrl}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                placeholder="https://your-server.onrender.com"
              />
              <Button title="Save server" variant="accent" onPress={saveServer} />
            </Card>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  container: { flexGrow: 1, paddingHorizontal: spacing.screen, justifyContent: 'center' },
  brand: { alignItems: 'center', marginBottom: spacing.lg },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    elevation: 4,
  },
  brandTitle: { fontSize: 26, fontWeight: '700', color: colors.textPrimary },
  cardTitle: { fontSize: fontSize.title, fontWeight: '600', color: colors.textPrimary, marginBottom: spacing.md },
  registerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: spacing.md },
  promptText: { fontSize: fontSize.body, color: colors.textSecondary },
  linkBtn: { minHeight: 40, justifyContent: 'center', paddingHorizontal: spacing.xs },
  link: { fontSize: fontSize.body, fontWeight: '600', color: colors.primary },
  serverToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    minHeight: 48,
    marginBottom: spacing.sm,
  },
  serverToggleText: { fontSize: fontSize.body, color: colors.textSecondary, marginHorizontal: spacing.xs },
});

