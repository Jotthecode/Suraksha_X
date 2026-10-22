import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, Alert } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { LeafletMapView } from '../components/LeafletMapView';
import { Screen, Card, SectionTitle, Button } from '../components/ui';
import { PlaceSearchField } from '../components/PlaceSearchField';
import { calculateSafeRoute, getCrimeHotspots, geocodeAddress } from '../api/config';
import { useSafety } from '../context/SafetyContext';
import { colors, spacing, radius, fontSize } from '../theme/colors';

const ROUTE_MODES = [
  { value: 0.2, label: 'Safest' },
  { value: 0.4, label: 'Balanced' },
  { value: 0.6, label: 'Faster' },
  { value: 0.8, label: 'Shortest' },
];

export const SafeRouteScreen = ({ navigation }) => {
  const { currentLocation } = useSafety();
  // Start from the user's own location (works anywhere in India); destination is typed
  const [origin, setOrigin] = useState('My current location');
  const [destination, setDestination] = useState('');
  const [originCoords, setOriginCoords] = useState({ lat: currentLocation.latitude, lon: currentLocation.longitude });
  const [destCoords, setDestCoords] = useState(null);
  const [alpha, setAlpha] = useState(0.40); // Trade-off parameter
  // Typed addresses are geocoded on calculate; "my location" already carries coordinates
  const [originDirty, setOriginDirty] = useState(false);
  const [destDirty, setDestDirty] = useState(false);

  // Follow GPS updates while the origin is still "my location"
  useEffect(() => {
    if (!originDirty && origin === 'My current location') {
      setOriginCoords({ lat: currentLocation.latitude, lon: currentLocation.longitude });
    }
  }, [currentLocation]);

  // Bias suggestions and searches towards where the user is (only once GPS has a real fix)
  const near = currentLocation.isRealGps ? { lat: currentLocation.latitude, lon: currentLocation.longitude } : null;

  // Only used when the user typed an address without picking a suggestion
  // (free OpenStreetMap search on the server; no API key needed)
  const geocode = async (text) => {
    const results = await geocodeAddress(text, near).catch(() => []);
    if (results.length > 0) return { lat: results[0].lat, lon: results[0].lon };
    throw new Error(`Could not find "${text}"`);
  };

  const useMyLocationAsOrigin = () => {
    setOrigin('My current location');
    setOriginCoords({ lat: currentLocation.latitude, lon: currentLocation.longitude });
    setOriginDirty(false);
  };

  const [isLoading, setIsLoading] = useState(false);
  const [routeResult, setRouteResult] = useState(null);
  const [hotspots, setHotspots] = useState([]);

  useEffect(() => {
    fetchHotspots(currentLocation.latitude, currentLocation.longitude);
  }, []);

  const fetchHotspots = async (lat, lon) => {
    try {
      const res = await getCrimeHotspots(lat, lon);
      if (res && res.hotspots) {
        setHotspots(res.hotspots);
      }
    } catch (e) {
      console.warn('Hotspots fetch error:', e);
    }
  };

  const handleComputeRoute = async () => {
    setIsLoading(true);
    let o = originCoords;
    let d = destCoords;
    if (!destination.trim()) {
      setIsLoading(false);
      Alert.alert('Destination needed', 'Type where you want to go, e.g. "Rajwada, Indore".');
      return;
    }
    try {
      if (originDirty && origin.trim()) {
        o = await geocode(origin.trim());
        setOriginCoords(o);
        setOriginDirty(false);
      }
      if ((destDirty || !d) && destination.trim()) {
        d = await geocode(destination.trim());
        setDestCoords(d);
        setDestDirty(false);
      }
    } catch (geoErr) {
      setIsLoading(false);
      Alert.alert('Address not found', `${geoErr.message}. Try a more specific address.`);
      return;
    }
    try {
      const res = await calculateSafeRoute({
        originLat: o.lat,
        originLon: o.lon,
        destLat: d.lat,
        destLon: d.lon,
        alpha,
      });
      setRouteResult(res);
      fetchHotspots((o.lat + d.lat) / 2, (o.lon + d.lon) / 2);
    } catch (err) {
      setRouteResult(null);
      const offline = /network|fetch|abort|HTTP Error/i.test(err?.message || '');
      Alert.alert(
        'Route unavailable',
        offline
          ? 'Could not reach the SurakshaX routing server. Check your internet connection and try again.'
          : err.message
      );
    } finally {
      setIsLoading(false);
    }
  };

  const safestPolyline = routeResult?.safest_route?.path_coords || [];
  const shortestPolyline = routeResult?.shortest_route?.path_coords || [];

  const markers = [
    { lat: originCoords.lat, lon: originCoords.lon, title: 'Origin', description: origin },
    ...(destCoords ? [{ lat: destCoords.lat, lon: destCoords.lon, title: 'Destination', description: destination, open: true }] : []),
  ];

  return (
    <Screen title="Safe route" onLeftPress={() => navigation.navigate('DashboardTab')}>
      <Card>
        <PlaceSearchField
          label="From"
          value={origin}
          near={near}
          onChangeText={(t) => { setOrigin(t); setOriginDirty(true); }}
          onSelect={(p) => {
            setOriginCoords({ lat: p.lat, lon: p.lon });
            setOriginDirty(false);
          }}
          placeholder="Start address"
        />
        <Pressable onPress={useMyLocationAsOrigin} style={styles.linkRow} hitSlop={8}>
          <MaterialIcons name="my-location" size={18} color={colors.accent} />
          <Text style={styles.linkText}>Use my location</Text>
        </Pressable>
        <PlaceSearchField
          label="To"
          value={destination}
          near={near}
          onChangeText={(t) => { setDestination(t); setDestDirty(true); }}
          onSelect={(p) => {
            setDestCoords({ lat: p.lat, lon: p.lon });
            setDestDirty(false);
          }}
          placeholder="Where to? e.g. Rajwada"
          returnKeyType="search"
          onSubmitEditing={handleComputeRoute}
        />

        <Text style={styles.fieldLabel}>Prefer</Text>
        <View style={styles.segment}>
          {ROUTE_MODES.map((m, i) => {
            const active = alpha === m.value;
            return (
              <Pressable
                key={m.value}
                onPress={() => setAlpha(m.value)}
                style={[styles.segmentItem, i > 0 && styles.segmentDivider, active && styles.segmentActive]}
              >
                <Text style={[styles.segmentText, active && styles.segmentTextActive]}>{m.label}</Text>
              </Pressable>
            );
          })}
        </View>

        <Button title="Find route" icon="directions" loading={isLoading} onPress={handleComputeRoute} />
      </Card>

      <SectionTitle>Map</SectionTitle>
      <Card padded={false}>
        <LeafletMapView
          centerLat={destCoords ? (originCoords.lat + destCoords.lat) / 2 : originCoords.lat}
          centerLon={destCoords ? (originCoords.lon + destCoords.lon) / 2 : originCoords.lon}
          zoom={12}
          markers={markers}
          hotspots={hotspots}
          safestRoute={safestPolyline}
          shortestRoute={shortestPolyline}
          style={styles.map}
        />
        <View style={styles.legend}>
          <LegendItem color={colors.safe} label="Safest" />
          <LegendItem color={colors.warning} label="Shortest" />
          <LegendItem color={colors.highRisk} label="Hotspot" />
        </View>
      </Card>

      {routeResult && (
        <>
          <SectionTitle>Result</SectionTitle>
          <Card>
            <View style={styles.compareRow}>
              <RouteStat
                title="Safest"
                tone={colors.safe}
                distance={routeResult.safest_route?.distance_km}
                risk={routeResult.safest_route?.average_risk_score}
              />
              <View style={styles.compareDivider} />
              <RouteStat
                title="Shortest"
                tone={colors.warning}
                distance={routeResult.shortest_route?.distance_km}
                risk={routeResult.shortest_route?.average_risk_score}
              />
            </View>
            {routeResult.tradeoff_summary ? (
              <Text style={styles.summary}>{routeResult.tradeoff_summary}</Text>
            ) : null}
            <Button
              title="Share live location"
              icon="share-location"
              variant="accent"
              onPress={() => navigation.navigate('LiveTrackingTab')}
              style={{ marginTop: spacing.md }}
            />
          </Card>
        </>
      )}
    </Screen>
  );
};

const LegendItem = ({ color, label }) => (
  <View style={styles.legendItem}>
    <View style={[styles.legendDot, { backgroundColor: color }]} />
    <Text style={styles.legendText}>{label}</Text>
  </View>
);

const RouteStat = ({ title, tone, distance, risk }) => (
  <View style={styles.compareCol}>
    <Text style={[styles.compareTitle, { color: tone }]}>{title}</Text>
    <Text style={styles.compareValue}>{distance != null ? `${distance.toFixed(1)} km` : '–'}</Text>
    <Text style={styles.compareSub}>Risk {((risk ?? 0) * 100).toFixed(0)}%</Text>
  </View>
);

const styles = StyleSheet.create({
  linkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    minHeight: 32,
    marginTop: -spacing.sm,
    marginBottom: spacing.sm,
  },
  linkText: { marginLeft: spacing.xs, fontSize: fontSize.body, fontWeight: '500', color: colors.accent },
  fieldLabel: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  segment: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    overflow: 'hidden',
    marginBottom: spacing.md,
  },
  segmentItem: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.cardBg },
  segmentDivider: { borderLeftWidth: 1, borderLeftColor: colors.border },
  segmentActive: { backgroundColor: colors.primaryLight },
  segmentText: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary },
  segmentTextActive: { color: colors.primaryDark, fontWeight: '700' },
  map: { height: 280, width: '100%' },
  legend: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: spacing.md },
  legendDot: { width: 10, height: 10, borderRadius: 5, marginRight: 6 },
  legendText: { fontSize: fontSize.caption, color: colors.textSecondary },
  compareRow: { flexDirection: 'row' },
  compareCol: { flex: 1 },
  compareDivider: { width: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginHorizontal: spacing.md },
  compareTitle: { fontSize: fontSize.caption, fontWeight: '700' },
  compareValue: { fontSize: fontSize.title, fontWeight: '700', color: colors.textPrimary, marginTop: spacing.xs },
  compareSub: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  summary: { fontSize: fontSize.body, color: colors.textSecondary, marginTop: spacing.md, lineHeight: 20 },
});
