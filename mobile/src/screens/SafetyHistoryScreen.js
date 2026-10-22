import React from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Screen, Card, EmptyState } from '../components/ui';
import { useSafety } from '../context/SafetyContext';
import { colors, spacing, fontSize } from '../theme/colors';

export const SafetyHistoryScreen = ({ navigation }) => {
  const { incidents, clearIncidentHistory } = useSafety();

  const handleClearHistory = () => {
    Alert.alert(
      'Clear SOS history?',
      'This deletes all past SOS records on this phone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Clear All', style: 'destructive', onPress: clearIncidentHistory },
      ]
    );
  };

  const fmt = (v) => (typeof v === 'number' ? v.toFixed(4) : v);

  return (
    <Screen
      title="SOS history"
      onLeftPress={() => navigation.goBack()}
      actions={incidents.length > 0 ? [{ icon: 'delete-outline', label: 'Clear history', onPress: handleClearHistory }] : []}
      bottomInset
    >
      {incidents.length === 0 ? (
        <EmptyState icon="history" title="No SOS alerts yet" message="Alerts you send will be listed here." />
      ) : (
        incidents.map((item, idx) => (
          <Card key={item.id || idx}>
            <View style={styles.topRow}>
              <Text style={styles.trigger} numberOfLines={2}>
                {item.trigger}
              </Text>
            </View>
            <Text style={styles.date}>
              {item.date_str}
              {item.id ? `  ·  ${item.id}` : ''}
            </Text>
            <DetailLine icon="place" text={`${fmt(item.latitude)}, ${fmt(item.longitude)}`} />
            <DetailLine icon="local-police" text={item.police || '–'} />
            <DetailLine icon="check-circle-outline" text={item.status || 'SMS and call sent'} />
          </Card>
        ))
      )}
    </Screen>
  );
};

const DetailLine = ({ icon, text }) => (
  <View style={styles.detail}>
    <MaterialIcons name={icon} size={16} color={colors.textMuted} />
    <Text style={styles.detailText} numberOfLines={2}>
      {text}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  topRow: { flexDirection: 'row', alignItems: 'center' },
  trigger: { flex: 1, fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary },
  date: { fontSize: fontSize.caption, color: colors.textMuted, marginTop: 2, marginBottom: spacing.sm },
  detail: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.xs },
  detailText: { flex: 1, marginLeft: spacing.sm, fontSize: fontSize.body, color: colors.textSecondary },
});
