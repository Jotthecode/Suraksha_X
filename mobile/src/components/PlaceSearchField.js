import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { suggestPlaces } from '../api/config';
import { colors, spacing, radius, fontSize, touchTarget } from '../theme/colors';

const DEBOUNCE_MS = 350;
const MIN_CHARS = 2;

/**
 * Text field with search-as-you-type place suggestions (nearest first).
 * Typing calls onChangeText; picking a suggestion calls onSelect({ name, subtitle, lat, lon }).
 * The list renders inline under the field, so it scrolls with the screen and never covers the keyboard.
 */
export const PlaceSearchField = ({
  label,
  value,
  onChangeText,
  onSelect,
  near,
  placeholder = 'Search a place',
  style,
  autoFocus,
  returnKeyType,
  onSubmitEditing,
}) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const requestId = useRef(0);
  const nearRef = useRef(near);
  nearRef.current = near;

  useEffect(() => {
    const query = (value || '').trim();
    if (!open || query.length < MIN_CHARS) {
      setResults([]);
      setLoading(false);
      setError('');
      return undefined;
    }
    const id = ++requestId.current;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const list = await suggestPlaces(query, nearRef.current);
        if (id !== requestId.current) return; // a newer keystroke already started another search
        setResults(list);
        setError(list.length ? '' : 'No matching places');
      } catch (e) {
        if (id === requestId.current) {
          setResults([]);
          setError('Search unavailable. Check your connection.');
        }
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [value, open]);

  const pick = (place) => {
    requestId.current++;
    setOpen(false);
    setResults([]);
    setError('');
    onChangeText?.(place.name);
    onSelect?.(place);
  };

  const showList = open && (value || '').trim().length >= MIN_CHARS && (loading || results.length > 0 || !!error);

  return (
    <View style={[styles.wrap, style]}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={[styles.inputRow, showList && styles.inputRowOpen]}>
        <MaterialIcons name="search" size={20} color={colors.textMuted} />
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={(t) => {
            setOpen(true);
            onChangeText?.(t);
          }}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
          autoCorrect={false}
          autoFocus={autoFocus}
          returnKeyType={returnKeyType}
          onSubmitEditing={onSubmitEditing}
        />
        {loading ? (
          <ActivityIndicator size="small" color={colors.accent} />
        ) : value ? (
          <Pressable
            onPress={() => {
              setOpen(false);
              onChangeText?.('');
            }}
            hitSlop={10}
            accessibilityLabel="Clear"
          >
            <MaterialIcons name="close" size={20} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      {showList ? (
        <View style={styles.list}>
          {results.map((place, i) => (
            <Pressable
              key={`${place.lat},${place.lon},${i}`}
              onPress={() => pick(place)}
              style={({ pressed }) => [styles.item, i > 0 && styles.itemDivider, pressed && styles.itemPressed]}
            >
              <MaterialIcons name="place" size={20} color={colors.primary} />
              <View style={styles.itemText}>
                <Text style={styles.itemName} numberOfLines={1}>
                  {place.name}
                </Text>
                {place.subtitle ? (
                  <Text style={styles.itemSub} numberOfLines={1}>
                    {place.subtitle}
                  </Text>
                ) : null}
              </View>
              {place.distance_km != null ? <Text style={styles.distance}>{place.distance_km} km</Text> : null}
            </Pressable>
          ))}
          {!results.length && error ? <Text style={styles.message}>{error}</Text> : null}
          {!results.length && loading ? <Text style={styles.message}>Searching…</Text> : null}
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: spacing.md },
  label: { fontSize: fontSize.caption, fontWeight: '600', color: colors.textSecondary, marginBottom: spacing.xs },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: touchTarget,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.cardBg,
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
  },
  inputRowOpen: { borderColor: colors.accent, borderBottomLeftRadius: 0, borderBottomRightRadius: 0 },
  input: { flex: 1, fontSize: fontSize.body, color: colors.textPrimary, paddingVertical: spacing.sm },
  list: {
    borderWidth: 1,
    borderTopWidth: 0,
    borderColor: colors.accent,
    borderBottomLeftRadius: radius.md,
    borderBottomRightRadius: radius.md,
    backgroundColor: colors.cardBg,
    overflow: 'hidden',
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: touchTarget + 8,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  itemDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.divider },
  itemPressed: { backgroundColor: colors.cardBgSecondary },
  itemText: { flex: 1 },
  itemName: { fontSize: fontSize.body, fontWeight: '600', color: colors.textPrimary },
  itemSub: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  distance: { fontSize: fontSize.caption, color: colors.textMuted },
  message: { padding: spacing.md, fontSize: fontSize.caption, color: colors.textSecondary },
});
