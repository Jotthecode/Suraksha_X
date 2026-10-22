import React, { useState } from 'react';
import { View, Text, StyleSheet, Switch, Pressable, Alert } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Screen, Card, SectionTitle, Button, TextField, Notice } from '../components/ui';
import { useTriggers } from '../context/TriggerContext';
import { matchTranscript, validateCodePhrase, MAX_PHRASES } from '../utils/phraseMatching';
import { colors, spacing, fontSize, touchTarget } from '../theme/colors';

const SwitchRow = ({ icon, label, hint, value, onChange, divider, disabled }) => (
  <View style={[styles.row, divider && styles.divider]}>
    <MaterialIcons name={icon} size={22} color={value ? colors.primary : colors.textSecondary} />
    <View style={styles.rowText}>
      <Text style={styles.rowLabel}>{label}</Text>
      {hint ? <Text style={styles.rowHint}>{hint}</Text> : null}
    </View>
    <Switch
      value={value}
      onValueChange={onChange}
      disabled={disabled}
      trackColor={{ false: colors.border, true: colors.highRiskBorder }}
      thumbColor={value ? colors.primary : '#F4F4F5'}
      accessibilityLabel={label}
    />
  </View>
);

export const SafetyTriggersScreen = ({ navigation }) => {
  const { settings, updateSettings, voiceStatus, voiceMode, speechSupported, motionState, motionStats } = useTriggers();
  const [newPhrase, setNewPhrase] = useState('');
  const [phraseError, setPhraseError] = useState('');
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState(null);

  const addPhrase = () => {
    const problem = validateCodePhrase(newPhrase, settings.codePhrases);
    if (problem) {
      setPhraseError(problem);
      return;
    }
    updateSettings({ codePhrases: [...settings.codePhrases, newPhrase.trim()] });
    setNewPhrase('');
    setPhraseError('');
  };

  const removePhrase = (phrase) => {
    Alert.alert('Remove code phrase?', `"${phrase}"`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: () => updateSettings({ codePhrases: settings.codePhrases.filter((p) => p !== phrase) }),
      },
    ]);
  };

  const runTest = () => {
    const match = matchTranscript(testText, {
      codePhrases: settings.codePhrases,
      useDistressWords: settings.useDistressWords,
      weakHits: {},
    });
    setTestResult(
      !testText.trim()
        ? null
        : match?.type === 'code'
        ? { ok: true, text: settings.silentCodePhrase ? 'Code phrase: sends a silent SOS' : 'Code phrase: starts the SOS countdown' }
        : match
        ? { ok: true, text: `Distress word "${match.word}": starts the SOS countdown` }
        : { ok: false, text: 'Would not trigger an SOS' }
    );
  };

  const codePhrasesUnavailable = settings.voiceEnabled && voiceMode === 'model';

  return (
    <Screen title="Safety triggers" onLeftPress={() => navigation.goBack()}>
      {/* Voice */}
      <SectionTitle>Voice</SectionTitle>
      <Card padded={false}>
        <SwitchRow
          icon={settings.voiceEnabled ? 'mic' : 'mic-none'}
          label="Listen for voice SOS"
          hint={settings.voiceEnabled ? voiceStatus : null}
          value={settings.voiceEnabled}
          onChange={(v) => updateSettings({ voiceEnabled: v })}
        />
        <SwitchRow
          icon="record-voice-over"
          label='"Bachao", "Help me", "Save me"'
          hint="Starts the SOS countdown"
          value={settings.useDistressWords}
          onChange={(v) => updateSettings({ useDistressWords: v })}
          divider
        />
      </Card>

      <SectionTitle>Code phrases</SectionTitle>
      <Card>
        <Text style={styles.body}>
          A normal-sounding sentence only you know, like "I left the stove on". Saying it sends an SOS without anyone
          around you knowing.
        </Text>
        {codePhrasesUnavailable || (!speechSupported && settings.voiceEnabled) ? (
          <Notice tone="warning" style={styles.notice}>
            This phone has no speech service, so only "Bachao" / "Help" are detected. Install or enable Google speech
            services to use code phrases.
          </Notice>
        ) : null}

        {settings.codePhrases.map((phrase) => (
          <View key={phrase} style={styles.phraseRow}>
            <MaterialIcons name="lock-outline" size={20} color={colors.textSecondary} />
            <Text style={styles.phraseText} numberOfLines={2}>
              {phrase}
            </Text>
            <Pressable onPress={() => removePhrase(phrase)} hitSlop={10} accessibilityLabel={`Remove ${phrase}`} style={styles.iconBtn}>
              <MaterialIcons name="delete-outline" size={22} color={colors.textSecondary} />
            </Pressable>
          </View>
        ))}

        {settings.codePhrases.length < MAX_PHRASES ? (
          <>
            <TextField
              label={settings.codePhrases.length ? 'Add another phrase' : 'Add a phrase'}
              value={newPhrase}
              onChangeText={(t) => {
                setNewPhrase(t);
                if (phraseError) setPhraseError('');
              }}
              placeholder="e.g. pass me the red umbrella"
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={addPhrase}
              style={styles.fieldTight}
            />
            {phraseError ? <Text style={styles.error}>{phraseError}</Text> : null}
            <Button title="Add phrase" icon="add" variant="outline" onPress={addPhrase} style={styles.addBtn} />
          </>
        ) : (
          <Text style={styles.rowHint}>You can save up to {MAX_PHRASES} phrases.</Text>
        )}
      </Card>
      <Card padded={false}>
        <SwitchRow
          icon="notifications-off"
          label="Silent SOS for code phrases"
          hint={
            settings.silentCodePhrase
              ? 'Sends at once: no SOS screen, sound or vibration'
              : 'Shows the 10-second SOS countdown first'
          }
          value={settings.silentCodePhrase}
          onChange={(v) => updateSettings({ silentCodePhrase: v })}
        />
      </Card>

      <SectionTitle>Try it</SectionTitle>
      <Card>
        <TextField
          value={testText}
          onChangeText={(t) => {
            setTestText(t);
            setTestResult(null);
          }}
          placeholder="Type what you'd say"
          returnKeyType="done"
          onSubmitEditing={runTest}
          style={styles.fieldTight}
        />
        <Button title="Check" variant="outline" onPress={runTest} style={styles.addBtn} />
        {testResult ? (
          <View style={styles.testResult}>
            <MaterialIcons
              name={testResult.ok ? 'check-circle' : 'remove-circle-outline'}
              size={20}
              color={testResult.ok ? colors.safe : colors.textSecondary}
            />
            <Text style={[styles.body, styles.testText]}>{testResult.text}</Text>
          </View>
        ) : null}
      </Card>

      {/* Motion */}
      <SectionTitle>Motion</SectionTitle>
      <Card padded={false}>
        <SwitchRow
          icon="vibration"
          label="Shake phone hard"
          hint="4 strong shakes within 2 seconds"
          value={settings.shakeEnabled}
          onChange={(v) => updateSettings({ shakeEnabled: v })}
        />
        <SwitchRow
          icon="directions-run"
          label="Sudden running"
          hint={
            settings.runEnabled && motionState.active
              ? `Now: ${motionStats.stepsPerMin} steps/min${motionStats.speedKmh != null ? ` · ${motionStats.speedKmh} km/h` : ''}`
              : 'Sprinting for about 8 seconds'
          }
          value={settings.runEnabled}
          onChange={(v) => updateSettings({ runEnabled: v })}
          divider
        />
      </Card>
      {motionState.error && (settings.shakeEnabled || settings.runEnabled) ? (
        <Notice tone="warning">{motionState.error}</Notice>
      ) : null}
      <Text style={styles.footnote}>
        Shake and running start the 10-second SOS countdown, so you can cancel a false alarm. Turn off running
        detection when you go jogging. Hands-free triggers work while SurakshaX is open.
      </Text>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: touchTarget + 8,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  divider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.divider },
  rowText: { flex: 1 },
  rowLabel: { fontSize: fontSize.body, fontWeight: '600', color: colors.textPrimary },
  rowHint: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  body: { fontSize: fontSize.body, color: colors.textSecondary, lineHeight: 20 },
  notice: { marginTop: spacing.sm },
  phraseRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: touchTarget,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  phraseText: { flex: 1, fontSize: fontSize.body, color: colors.textPrimary, fontWeight: '500' },
  iconBtn: { width: touchTarget, height: touchTarget, alignItems: 'center', justifyContent: 'center' },
  fieldTight: { marginTop: spacing.md, marginBottom: spacing.sm },
  error: { color: colors.primary, fontSize: fontSize.caption, marginBottom: spacing.sm },
  addBtn: { marginTop: spacing.xs },
  testResult: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.md },
  testText: { flex: 1 },
  footnote: {
    fontSize: fontSize.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
  },
});
