import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Share, Linking, Alert } from 'react-native';
import * as Location from 'expo-location';
import * as Battery from 'expo-battery';
import { LeafletMapView } from '../components/LeafletMapView';
import { Screen, Card, SectionTitle, Button, ButtonRow, Chip, Notice } from '../components/ui';
import { streamGpsUpdate, getLiveTrackingUrl } from '../api/config';
import { getLocationQuietly } from '../utils/location';
import { useSafety } from '../context/SafetyContext';
import { colors, spacing, radius, fontSize } from '../theme/colors';

export const LiveTrackingScreen = ({ navigation }) => {
  const { currentLocation, user } = useSafety();

  // 128-bit random id: the tracking link is the only secret protecting the live location
  const [sessionId] = useState(() =>
    Array.from({ length: 32 }, () => '0123456789abcdef'[Math.floor(Math.random() * 16)]).join('')
  );
  const [trackingUrl, setTrackingUrl] = useState('');
  const [packetCount, setPacketCount] = useState(0);
  const [isStreaming, setIsStreaming] = useState(true);
  const [liveCoords, setLiveCoords] = useState(currentLocation);

  const streamInterval = useRef(null);
  const [battery, setBattery] = useState(null);
  const [accuracyM, setAccuracyM] = useState(null);
  const [streamStatus, setStreamStatus] = useState(null);

  useEffect(() => {
    initTrackingUrl();
    startTrackingStream();

    return () => {
      if (streamInterval.current) clearInterval(streamInterval.current);
    };
  }, []);

  const initTrackingUrl = async () => {
    const url = await getLiveTrackingUrl(sessionId);
    setTrackingUrl(url);
  };

  const startTrackingStream = () => {
    setIsStreaming(true);

    // Initial packet
    sendPacket();

    // 5-second recurring stream matching research architecture Module 3
    streamInterval.current = setInterval(() => {
      sendPacket();
    }, 5000);
  };

  const stopTrackingStream = () => {
    if (streamInterval.current) {
      clearInterval(streamInterval.current);
      streamInterval.current = null;
    }
    setIsStreaming(false);
  };

  const sendPacket = async () => {
    try {
      const loc = await getLocationQuietly();
      if (!loc) {
        setStreamStatus('Waiting for GPS fix…');
        return; // never stream placeholder coordinates
      }
      const lat = loc.coords.latitude;
      const lon = loc.coords.longitude;
      setLiveCoords({ latitude: lat, longitude: lon });
      setAccuracyM(loc.coords.accuracy);

      let batteryPct = null;
      try {
        const level = await Battery.getBatteryLevelAsync();
        if (level >= 0) batteryPct = Math.round(level * 100);
      } catch (e) {}
      setBattery(batteryPct);

      await streamGpsUpdate({
        sessionId,
        userName: user.name,
        latitude: lat,
        longitude: lon,
        speed: loc.coords.speed || 0.0,
        accuracy: loc.coords.accuracy || 0,
        battery: batteryPct ?? 0,
      });

      setPacketCount((c) => c + 1);
      setStreamStatus(null);
    } catch (e) {
      console.warn('Packet stream error:', e.message);
      setStreamStatus('Server unreachable – retrying every 5 s');
    }
  };

  const handleShareLink = async () => {
    try {
      await Share.share({
        message: `I'm sharing my live location from SurakshaX. Track me here:
${trackingUrl}`,
        title: 'My live location',
      });
    } catch (error) {
      Alert.alert('Error', 'Unable to open share dialogue');
    }
  };

  const handleOpenBrowser = () => {
    if (trackingUrl) {
      Linking.openURL(trackingUrl).catch(() => {
        Alert.alert('Error', 'Cannot open browser');
      });
    }
  };

  const markers = [
    {
      lat: liveCoords.latitude,
      lon: liveCoords.longitude,
      title: 'You are here',
      description: `Updates sent: ${packetCount}`,
      open: true,
    },
  ];

  return (
    <Screen title="Live location" onLeftPress={() => navigation.navigate('DashboardTab')}>
      <Card>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Status</Text>
          <Chip
            label={isStreaming ? 'Sharing' : 'Paused'}
            icon={isStreaming ? 'wifi-tethering' : 'pause'}
            tone={isStreaming ? 'safe' : 'warning'}
          />
        </View>

        <View style={styles.statsGrid}>
          <Stat label="Updates sent" value={String(packetCount)} />
          <Stat label="Every" value="5 s" />
          <Stat label="Battery" value={battery != null ? `${battery}%` : '–'} />
          <Stat label="Accuracy" value={accuracyM != null ? `±${Math.round(accuracyM)} m` : '–'} />
        </View>

        {streamStatus ? <Notice icon="warning-amber">{streamStatus}</Notice> : null}

        <Text style={styles.fieldLabel}>Tracking link</Text>
        <View style={styles.linkBox}>
          <Text style={styles.linkText} numberOfLines={1} selectable>
            {trackingUrl || 'Generating link…'}
          </Text>
        </View>

        <ButtonRow style={{ marginBottom: spacing.sm }}>
          <Button title="Share link" icon="share" variant="accent" onPress={handleShareLink} disabled={!trackingUrl} />
          <Button title="Open map" icon="open-in-new" variant="outline" onPress={handleOpenBrowser} disabled={!trackingUrl} />
        </ButtonRow>

        <Button
          title={isStreaming ? 'Pause sharing' : 'Resume sharing'}
          icon={isStreaming ? 'pause' : 'play-arrow'}
          variant={isStreaming ? 'dangerOutline' : 'safe'}
          onPress={isStreaming ? stopTrackingStream : startTrackingStream}
        />
      </Card>

      <SectionTitle
        right={
          <Text style={styles.coords}>
            {liveCoords.latitude.toFixed(5)}, {liveCoords.longitude.toFixed(5)}
          </Text>
        }
      >
        Map
      </SectionTitle>
      <Card padded={false}>
        <LeafletMapView
          centerLat={liveCoords.latitude}
          centerLon={liveCoords.longitude}
          zoom={15}
          markers={markers}
          style={styles.map}
        />
      </Card>
    </Screen>
  );
};

const Stat = ({ label, value }) => (
  <View style={styles.statCell}>
    <View style={styles.statBox}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  statusLabel: { fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -spacing.xs, marginBottom: spacing.sm },
  statCell: { width: '50%', padding: spacing.xs },
  statBox: {
    backgroundColor: colors.cardBgSecondary,
    borderRadius: radius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    paddingVertical: 12,
    paddingHorizontal: 12,
  },
  statValue: { fontSize: fontSize.section, fontWeight: '700', color: colors.textPrimary },
  statLabel: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  fieldLabel: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  linkBox: {
    minHeight: 44,
    justifyContent: 'center',
    backgroundColor: colors.accentLight,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  linkText: { fontSize: fontSize.caption, color: colors.accentDark, fontFamily: 'monospace' },
  coords: { fontSize: fontSize.caption, color: colors.textSecondary },
  map: { height: 300, width: '100%' },
});
