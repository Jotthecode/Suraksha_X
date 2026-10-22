import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Linking, ActivityIndicator, Alert } from 'react-native';
import { Screen, Card, SectionTitle, Button, ButtonRow, ListRow, Chip, EmptyState } from '../components/ui';
import { getNearestPoliceStations } from '../api/config';
import { useSafety } from '../context/SafetyContext';
import { colors, spacing, fontSize } from '../theme/colors';

export const PoliceStationsScreen = ({ navigation }) => {
  const { currentLocation } = useSafety();

  const [stations, setStations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchStations();
  }, [currentLocation]);

  const fetchStations = async () => {
    setIsLoading(true);
    try {
      const res = await getNearestPoliceStations(
        currentLocation.latitude,
        currentLocation.longitude,
        6
      );
      const list = (res && res.stations) || [];
      // Only show stations that are realistically reachable
      const nearby = list.filter((st) => st.distance_km <= 50);
      setStations(nearby);
      if (list.length > 0 && nearby.length === 0) {
        Alert.alert('Outside coverage area', 'No mapped police station within 50 km of you. Call 112 for emergency help.');
      }
    } catch (e) {
      setStations([]);
      Alert.alert('Offline', 'Cannot load nearby police stations. Call 112 for emergency help.');
    } finally {
      setIsLoading(false);
    }
  };

  const callStation = (phone) => {
    Linking.openURL(`tel:${phone}`).catch(() => {
      Alert.alert('Call Error', `Unable to call ${phone}`);
    });
  };

  const openInMaps = (st) => {
    const label = encodeURIComponent(st.name);
    Linking.openURL(`geo:${st.lat},${st.lon}?q=${st.lat},${st.lon}(${label})`).catch(() => {
      Alert.alert('Map Error', 'Unable to open maps');
    });
  };

  return (
    <Screen
      title="Nearby police"
      onLeftPress={() => navigation.goBack()}
      actions={[{ icon: 'refresh', label: 'Refresh', onPress: fetchStations }]}
      bottomInset
    >
      <Card padded={false}>
        <ListRow
          icon="local-police"
          iconColor={colors.primary}
          label="Emergency police"
          value="112"
          right={<Button title="Call" icon="call" compact onPress={() => callStation('112')} style={styles.callBtn} />}
        />
      </Card>

      <SectionTitle>Police stations</SectionTitle>
      {isLoading ? (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={colors.accent} />
          <Text style={styles.loadingText}>Finding police stations…</Text>
        </View>
      ) : stations.length === 0 ? (
        <EmptyState icon="local-police" title="No stations found" message="Call 112 for emergency help." />
      ) : (
        stations.map((st, idx) => (
          <Card key={idx}>
            <View style={styles.stationHeader}>
              <View style={styles.flex}>
                <Text style={styles.stationName}>{st.name}</Text>
                <Text style={styles.stationAddress} numberOfLines={2}>
                  {st.address || st.jurisdiction || 'Address not available'}
                </Text>
              </View>
              <View style={styles.distance}>
                <Chip label={`${st.distance_km.toFixed(1)} km`} />
                <Text style={styles.eta}>~{st.eta_minutes || Math.round(st.distance_km * 2.5)} min</Text>
              </View>
            </View>
            <ButtonRow>
              <Button title={st.phone ? String(st.phone) : 'Call'} icon="call" variant="safe" onPress={() => callStation(st.phone)} />
              <Button title="Directions" icon="directions" variant="outline" onPress={() => openInMaps(st)} />
            </ButtonRow>
          </Card>
        ))
      )}
    </Screen>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  callBtn: { marginLeft: spacing.md, minHeight: 40 },
  loading: { alignItems: 'center', paddingVertical: spacing.xl },
  loadingText: { marginTop: spacing.sm, fontSize: fontSize.body, color: colors.textSecondary },
  stationHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 12 },
  stationName: { fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary },
  stationAddress: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  distance: { alignItems: 'flex-end', marginLeft: spacing.sm },
  eta: { fontSize: fontSize.caption, color: colors.textMuted, marginTop: spacing.xs },
});
