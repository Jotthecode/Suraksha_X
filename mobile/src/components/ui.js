// Small shared building blocks so every screen uses the same spacing, type and touch sizes.
import React from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { colors, spacing, radius, fontSize, touchTarget } from '../theme/colors';
import { AppHeader } from './AppHeader';

/**
 * Screen = AppHeader + scrollable, keyboard-aware body with 16dp side padding.
 * Pass `scroll={false}` to render children in a plain flex container.
 * `bottomInset` adds the bottom safe-area (use on stack screens without a tab bar).
 */
export const Screen = ({
  title,
  leftIcon = 'back',
  onLeftPress,
  actions,
  children,
  scroll = true,
  bottomInset = false,
  contentStyle,
  banner,
}) => {
  const insets = useSafeAreaInsets();
  const bottomPad = spacing.lg + (bottomInset ? insets.bottom : 0);
  return (
    <View style={styles.screen}>
      <AppHeader title={title} leftIcon={leftIcon} onLeftPress={onLeftPress} actions={actions} />
      {banner}
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        {scroll ? (
          <ScrollView
            style={styles.flex}
            contentContainerStyle={[styles.content, { paddingBottom: bottomPad }, contentStyle]}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {children}
          </ScrollView>
        ) : (
          <View style={[styles.flex, contentStyle]}>{children}</View>
        )}
      </KeyboardAvoidingView>
    </View>
  );
};

export const Card = ({ children, style, padded = true }) => (
  <View style={[styles.card, padded && styles.cardPadded, style]}>{children}</View>
);

export const SectionTitle = ({ children, right, style }) => (
  <View style={[styles.sectionRow, style]}>
    <Text style={styles.sectionTitle}>{children}</Text>
    {right}
  </View>
);

export const IconCircle = ({ name, color = colors.primary, bg = colors.primaryLight, size = 40 }) => (
  <View style={[styles.iconCircle, { width: size, height: size, borderRadius: size / 2, backgroundColor: bg }]}>
    <MaterialIcons name={name} size={Math.round(size * 0.55)} color={color} />
  </View>
);

/** One list row: icon, label (+ optional secondary line), value, chevron. 56dp min height. */
export const ListRow = ({
  icon,
  iconColor = colors.textSecondary,
  label,
  secondary,
  value,
  onPress,
  chevron = !!onPress,
  right,
  divider = false,
  danger = false,
}) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    android_ripple={onPress ? { color: colors.divider } : undefined}
    style={({ pressed }) => [styles.listRow, divider && styles.listRowDivider, pressed && onPress && styles.pressed]}
  >
    {icon ? (
      <MaterialIcons
        name={icon}
        size={22}
        color={danger ? colors.primary : iconColor}
        style={styles.listRowIcon}
      />
    ) : null}
    <View style={styles.flex}>
      <Text style={[styles.listRowLabel, danger && { color: colors.primary }]} numberOfLines={1}>
        {label}
      </Text>
      {secondary ? (
        <Text style={styles.listRowSecondary} numberOfLines={2}>
          {secondary}
        </Text>
      ) : null}
    </View>
    {value ? <Text style={styles.listRowValue}>{value}</Text> : null}
    {right}
    {chevron ? <MaterialIcons name="chevron-right" size={22} color={colors.textMuted} /> : null}
  </Pressable>
);

const BUTTON_VARIANTS = {
  primary: { bg: colors.primary, fg: colors.textLight, border: colors.primary },
  accent: { bg: colors.accent, fg: colors.textLight, border: colors.accent },
  safe: { bg: colors.safe, fg: colors.textLight, border: colors.safe },
  outline: { bg: colors.cardBg, fg: colors.accent, border: colors.border },
  dangerOutline: { bg: colors.cardBg, fg: colors.primary, border: colors.highRiskBorder },
  dark: { bg: colors.textPrimary, fg: colors.textLight, border: colors.textPrimary },
};

export const Button = ({ title, onPress, variant = 'primary', icon, loading = false, disabled = false, style, compact = false }) => {
  const v = BUTTON_VARIANTS[variant] || BUTTON_VARIANTS.primary;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      android_ripple={{ color: 'rgba(0,0,0,0.12)' }}
      style={({ pressed }) => [
        styles.button,
        compact && styles.buttonCompact,
        { backgroundColor: v.bg, borderColor: v.border },
        (disabled || loading) && styles.disabled,
        pressed && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={v.fg} />
      ) : (
        <>
          {icon ? <MaterialIcons name={icon} size={20} color={v.fg} style={styles.buttonIcon} /> : null}
          <Text style={[styles.buttonText, { color: v.fg }]} numberOfLines={1}>
            {title}
          </Text>
        </>
      )}
    </Pressable>
  );
};

/** Evenly split row of buttons. */
export const ButtonRow = ({ children, style }) => (
  <View style={[styles.buttonRow, style]}>
    {React.Children.toArray(children).filter(Boolean).map((child, i) => (
      <View key={i} style={[styles.flex, i > 0 && { marginLeft: spacing.sm }]}>
        {child}
      </View>
    ))}
  </View>
);

export const TextField = ({ label, style, inputStyle, ...props }) => (
  <View style={[styles.field, style]}>
    {label ? <Text style={styles.fieldLabel}>{label}</Text> : null}
    <TextInput placeholderTextColor={colors.textMuted} style={[styles.input, inputStyle]} {...props} />
  </View>
);

export const Chip = ({ label, selected = false, onPress, icon, tone = 'default', disabled }) => {
  const toneStyle =
    tone === 'safe'
      ? { bg: colors.safeLight, fg: colors.safe, border: colors.safeBorder }
      : tone === 'danger'
      ? { bg: colors.highRiskLight, fg: colors.highRisk, border: colors.highRiskBorder }
      : tone === 'warning'
      ? { bg: colors.warningLight, fg: colors.warning, border: colors.warningBorder }
      : selected
      ? { bg: colors.primaryLight, fg: colors.primaryDark, border: colors.primary }
      : { bg: colors.cardBg, fg: colors.textSecondary, border: colors.border };
  const Wrapper = onPress ? Pressable : View;
  return (
    <Wrapper
      onPress={onPress}
      disabled={disabled}
      style={[styles.chip, { backgroundColor: toneStyle.bg, borderColor: toneStyle.border }, onPress && styles.chipTouchable]}
    >
      {icon ? <MaterialIcons name={icon} size={16} color={toneStyle.fg} style={{ marginRight: 4 }} /> : null}
      <Text style={[styles.chipText, { color: toneStyle.fg }]} numberOfLines={1}>
        {label}
      </Text>
    </Wrapper>
  );
};

export const EmptyState = ({ icon, title, message }) => (
  <Card style={styles.empty}>
    <MaterialIcons name={icon} size={40} color={colors.textMuted} />
    <Text style={styles.emptyTitle}>{title}</Text>
    {message ? <Text style={styles.emptyMessage}>{message}</Text> : null}
  </Card>
);

export const Notice = ({ tone = 'warning', icon = 'info-outline', children, style }) => {
  const t =
    tone === 'safe'
      ? { bg: colors.safeLight, fg: colors.safe }
      : tone === 'danger'
      ? { bg: colors.highRiskLight, fg: colors.primaryDark }
      : tone === 'info'
      ? { bg: colors.accentLight, fg: colors.accentDark }
      : { bg: colors.warningLight, fg: colors.warning };
  return (
    <View style={[styles.notice, { backgroundColor: t.bg }, style]}>
      <MaterialIcons name={icon} size={18} color={t.fg} style={{ marginRight: spacing.sm, marginTop: 1 }} />
      <Text style={[styles.noticeText, { color: t.fg }]}>{children}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { paddingHorizontal: spacing.screen, paddingTop: spacing.md },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.md,
    marginBottom: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    elevation: 1,
    shadowColor: colors.shadowColor,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    overflow: 'hidden',
  },
  cardPadded: { padding: spacing.md },
  sectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
    marginTop: spacing.xs,
  },
  sectionTitle: { fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary },
  iconCircle: { alignItems: 'center', justifyContent: 'center' },
  listRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.cardBg,
  },
  listRowDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  listRowIcon: { marginRight: spacing.md },
  listRowLabel: { fontSize: fontSize.body, fontWeight: '500', color: colors.textPrimary },
  listRowSecondary: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  listRowValue: { fontSize: fontSize.body, color: colors.textSecondary, marginLeft: spacing.sm },
  pressed: { opacity: 0.85 },
  disabled: { opacity: 0.6 },
  button: {
    minHeight: touchTarget,
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  buttonCompact: { paddingHorizontal: spacing.sm },
  buttonIcon: { marginRight: spacing.sm },
  buttonText: { fontSize: fontSize.body, fontWeight: '600' },
  buttonRow: { flexDirection: 'row', alignItems: 'stretch' },
  field: { marginBottom: spacing.md },
  fieldLabel: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  input: {
    minHeight: touchTarget,
    backgroundColor: colors.cardBgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: fontSize.body,
    color: colors.textPrimary,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  chipTouchable: { minHeight: 36, marginRight: spacing.sm, marginBottom: spacing.sm },
  chipText: { fontSize: fontSize.caption, fontWeight: '600' },
  empty: { alignItems: 'center', paddingVertical: spacing.xl },
  emptyTitle: { fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary, marginTop: spacing.sm },
  emptyMessage: { fontSize: fontSize.body, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xs },
  notice: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderRadius: radius.sm,
    padding: 12,
    marginBottom: spacing.md,
  },
  noticeText: { flex: 1, fontSize: fontSize.body, lineHeight: 20 },
});
export const uiStyles = styles;
