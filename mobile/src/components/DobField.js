// Date of birth as three small numeric inputs (DD / MM / YYYY) — no native date picker needed.
import React, { useRef } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { colors, spacing, radius, fontSize, touchTarget } from '../theme/colors';

/** value: { day, month, year } strings. Focus jumps to the next box when one is full. */
export const DobField = ({ label = 'Date of birth (optional)', value, onChange, error }) => {
  const monthRef = useRef(null);
  const yearRef = useRef(null);
  const set = (key, text, max, nextRef) => {
    const digits = text.replace(/\D/g, '').slice(0, max);
    onChange({ ...value, [key]: digits });
    if (digits.length === max && nextRef) nextRef.current?.focus?.();
  };
  const boxStyle = [styles.box, error && styles.boxError];
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        <TextInput
          style={boxStyle}
          value={value.day}
          onChangeText={(t) => set('day', t, 2, monthRef)}
          placeholder="DD"
          placeholderTextColor={colors.textMuted}
          keyboardType="number-pad"
          maxLength={2}
          accessibilityLabel="Day"
        />
        <Text style={styles.sep}>/</Text>
        <TextInput
          ref={monthRef}
          style={boxStyle}
          value={value.month}
          onChangeText={(t) => set('month', t, 2, yearRef)}
          placeholder="MM"
          placeholderTextColor={colors.textMuted}
          keyboardType="number-pad"
          maxLength={2}
          accessibilityLabel="Month"
        />
        <Text style={styles.sep}>/</Text>
        <TextInput
          ref={yearRef}
          style={[boxStyle, styles.year]}
          value={value.year}
          onChangeText={(t) => set('year', t, 4)}
          placeholder="YYYY"
          placeholderTextColor={colors.textMuted}
          keyboardType="number-pad"
          maxLength={4}
          accessibilityLabel="Year"
        />
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: spacing.md },
  label: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  row: { flexDirection: 'row', alignItems: 'center' },
  box: {
    width: 64,
    minHeight: touchTarget,
    backgroundColor: colors.cardBgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    textAlign: 'center',
    fontSize: fontSize.body,
    color: colors.textPrimary,
  },
  boxError: { borderColor: colors.primary },
  year: { width: 88 },
  sep: { marginHorizontal: spacing.sm, fontSize: fontSize.section, color: colors.textMuted },
  error: { fontSize: fontSize.caption, color: colors.primary, marginTop: spacing.xs },
});
