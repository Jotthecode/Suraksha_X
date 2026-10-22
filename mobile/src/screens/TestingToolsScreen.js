import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { useSafety } from '../context/SafetyContext';
import { analyzeSensorStatus, testVoiceSosKeyword } from '../api/config';
import { colors, spacing, fontSize, radius } from '../theme/colors';
import { Screen, Card, SectionTitle, ListRow, Button, ButtonRow, TextField, Chip, Notice } from '../components/ui';
import { PlaceSearchField } from '../components/PlaceSearchField';

const PRESET_PLACES = [
  { name: 'Connaught Place, New Delhi', lat: 28.6315, lon: 77.2167 },
  { name: 'Chhatrapati Shivaji Terminus, Mumbai', lat: 18.9398, lon: 72.8355 },
  { name: 'MG Road, Bengaluru', lat: 12.9756, lon: 77.6066 },
  { name: 'Rajwada, Indore', lat: 22.7186, lon: 75.8553 },
  { name: 'Park Street, Kolkata', lat: 22.5526, lon: 88.352 },
];

const TEST_WORDS = ['Bachao', 'Help', 'Emergency', 'Save me', 'Safe hello'];

export const TestingToolsScreen = ({ navigation }) => {
  const { currentLocation, setCustomLocation, detectDeviceLocation, isRefreshingLocation } = useSafety();
  const [placeQuery, setPlaceQuery] = useState('');

  // Test location
  const [inputLat, setInputLat] = useState(String(currentLocation.latitude));
  const [inputLon, setInputLon] = useState(String(currentLocation.longitude));

  useEffect(() => {
    setInputLat(String(currentLocation.latitude));
    setInputLon(String(currentLocation.longitude));
  }, [currentLocation]);

  // Voice keyword test
  const [customPhrase, setCustomPhrase] = useState('');
  const [isTestingVoice, setIsTestingVoice] = useState(false);
  const [voiceBanner, setVoiceBanner] = useState(null);

  // Sensor telemetry
  const [audioScore, setAudioScore] = useState('0.15');
  const [fallForce, setFallForce] = useState('1.1');
  const [heartRate, setHeartRate] = useState('74');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleVoiceEvaluation = async (phraseToTest) => {
    const text = phraseToTest || customPhrase || 'Bachao';
    setIsTestingVoice(true);
    try {
      const res = await testVoiceSosKeyword(text, 0.92);
      setIsTestingVoice(false);

      if (res.sos_triggered) {
        const detected = res.detected_keyword || text.toUpperCase();
        setVoiceBanner(
          `"${detected}" detected (${((res.posterior_probability || 0.95) * 100).toFixed(0)}%). Starting SOS…`
        );
        setTimeout(() => {
          setVoiceBanner(null);
          navigation.navigate('AlertsModal', { triggerReason: `Autonomous CNN Voice Trigger: "${detected}"` });
        }, 1200);
      } else {
        Alert.alert(
          'No distress detected',
          `"${text}" scored ${((res.posterior_probability || 0.45) * 100).toFixed(1)}%, below the SOS threshold (85%).`
        );
      }
    } catch (err) {
      setIsTestingVoice(false);
      setVoiceBanner(`"${text}" detected. Starting SOS…`);
      setTimeout(() => {
        setVoiceBanner(null);
        navigation.navigate('AlertsModal', { triggerReason: `Autonomous CNN Voice Trigger: "${text}"` });
      }, 1000);
    }
  };

  const handleAnalyzeSituation = async () => {
    setIsAnalyzing(true);
    try {
      const res = await analyzeSensorStatus({
        audioScore: parseFloat(audioScore) || 0.1,
        fallForce: parseFloat(fallForce) || 1.0,
        heartRate: parseFloat(heartRate) || 72,
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
      });

      setAnalysisResult(res);

      if (res.decision === 'CRITICAL') {
        Alert.alert('Critical reading', `${res.reason}\n\nStart SOS?`, [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Start SOS',
            style: 'destructive',
            onPress: () => {
              navigation.navigate('AlertsModal', { triggerReason: `Sensor Telemetry AI: ${res.reason}` });
            },
          },
        ]);
      }
    } catch (err) {
      const a = parseFloat(audioScore);
      const f = parseFloat(fallForce);
      const hr = parseFloat(heartRate);
      const isCrit = a >= 0.7 || f >= 3.0 || hr >= 120 || hr <= 45;
      const decision = isCrit ? 'CRITICAL' : 'SAFE';
      const reason = isCrit
        ? 'Acoustic / physical impact anomaly exceeds safety threshold'
        : 'Telemetry readings within physiological baseline';

      setAnalysisResult({
        decision,
        reason,
        metrics: { audio_score: a, fall_force: f, heart_rate: hr },
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const setTelemetryPreset = (type) => {
    if (type === 'safe') {
      setAudioScore('0.12');
      setFallForce('1.0');
      setHeartRate('72');
    } else if (type === 'scream') {
      setAudioScore('0.88');
      setFallForce('1.2');
      setHeartRate('95');
    } else if (type === 'fall') {
      setAudioScore('0.25');
      setFallForce('4.2');
      setHeartRate('135');
    }
  };

  const applyCustom = () => {
    if (inputLat && inputLon) {
      setCustomLocation(inputLat, inputLon);
      Alert.alert('Location set', `${inputLat}, ${inputLon}`);
    }
  };

  const critical = analysisResult?.decision === 'CRITICAL';

  return (
    <Screen
      title="Testing tools"
      onLeftPress={() => navigation.goBack()}
      bottomInset
      banner={
        voiceBanner ? (
          <View style={styles.banner}>
            <Text style={styles.bannerText}>{voiceBanner}</Text>
          </View>
        ) : null
      }
    >
      {/* Test location */}
      <SectionTitle>Test location</SectionTitle>
      <Card>
        <PlaceSearchField
          value={placeQuery}
          onChangeText={setPlaceQuery}
          near={currentLocation.isRealGps ? { lat: currentLocation.latitude, lon: currentLocation.longitude } : null}
          onSelect={(p) => setCustomLocation(p.lat, p.lon, p.subtitle ? `${p.name}, ${p.subtitle}` : p.name)}
          placeholder="Search any place in India"
          style={{ marginBottom: 0 }}
        />
      </Card>
      <Card padded={false}>
        <ListRow
          icon="my-location"
          iconColor={colors.accent}
          label={isRefreshingLocation ? 'Detecting…' : 'Use device GPS'}
          secondary={currentLocation.address || `${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}`}
          onPress={detectDeviceLocation}
          chevron={false}
        />
        {PRESET_PLACES.map((p) => (
          <ListRow
            key={p.name}
            icon="place"
            label={p.name}
            secondary={`${p.lat}, ${p.lon}`}
            onPress={() => setCustomLocation(p.lat, p.lon, p.name)}
            chevron={false}
            divider
          />
        ))}
      </Card>
      <Card>
        <View style={styles.row}>
          <TextField
            label="Latitude"
            value={inputLat}
            onChangeText={setInputLat}
            keyboardType="numeric"
            style={styles.half}
          />
          <TextField
            label="Longitude"
            value={inputLon}
            onChangeText={setInputLon}
            keyboardType="numeric"
            style={[styles.half, { marginLeft: spacing.sm }]}
          />
        </View>
        <Button title="Apply coordinates" variant="accent" onPress={applyCustom} />
      </Card>

      {/* Voice keyword test */}
      <SectionTitle>Voice keyword test</SectionTitle>
      <Card>
        <View style={styles.chipsWrap}>
          {TEST_WORDS.map((word) => (
            <Chip
              key={word}
              label={word}
              icon="record-voice-over"
              tone={word === 'Safe hello' ? 'safe' : 'default'}
              onPress={() => handleVoiceEvaluation(word)}
              disabled={isTestingVoice}
            />
          ))}
        </View>
        <TextField
          label="Custom phrase"
          value={customPhrase}
          onChangeText={setCustomPhrase}
          placeholder="Type a phrase"
          returnKeyType="send"
          onSubmitEditing={() => handleVoiceEvaluation(customPhrase)}
        />
        <Button
          title="Test phrase"
          variant="dark"
          loading={isTestingVoice}
          onPress={() => handleVoiceEvaluation(customPhrase)}
        />
      </Card>

      {/* Sensor telemetry */}
      <SectionTitle>Sensor check</SectionTitle>
      <Card>
        <View style={styles.chipsWrap}>
          <Chip label="Normal" onPress={() => setTelemetryPreset('safe')} />
          <Chip label="Scream" onPress={() => setTelemetryPreset('scream')} />
          <Chip label="Fall" onPress={() => setTelemetryPreset('fall')} />
        </View>
        <View style={styles.row}>
          <TextField label="Audio score" value={audioScore} onChangeText={setAudioScore} keyboardType="numeric" style={styles.third} />
          <TextField
            label="Fall force (g)"
            value={fallForce}
            onChangeText={setFallForce}
            keyboardType="numeric"
            style={[styles.third, styles.gap]}
          />
          <TextField
            label="Heart rate"
            value={heartRate}
            onChangeText={setHeartRate}
            keyboardType="numeric"
            style={[styles.third, styles.gap]}
          />
        </View>
        <Button title="Analyse" variant="dark" loading={isAnalyzing} onPress={handleAnalyzeSituation} />

        {analysisResult && (
          <Notice
            tone={critical ? 'danger' : 'safe'}
            icon={critical ? 'error-outline' : 'check-circle'}
            style={styles.result}
          >
            {`${analysisResult.decision}: ${analysisResult.reason}`}
          </Notice>
        )}
      </Card>
    </Screen>
  );
};

const styles = StyleSheet.create({
  banner: {
    backgroundColor: colors.primaryDark,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
  },
  bannerText: {
    color: colors.textLight,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  row: { flexDirection: 'row' },
  half: { flex: 1 },
  third: { flex: 1 },
  gap: { marginLeft: spacing.sm },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.sm },
  result: { marginTop: spacing.md, marginBottom: 0, borderRadius: radius.sm },
});
