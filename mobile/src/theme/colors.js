// SurakshaX colour palette & design tokens
export const colors = {
  primary: '#D32F2F',       // Emergency Crimson / Primary
  primaryDark: '#B71C1C',
  primaryLight: '#FFEBEE',
  primaryHover: '#C62828',

  accent: '#1B64DA',        // Samsung One UI Signature Blue
  accentDark: '#0D47A1',
  accentLight: '#E8F0FE',

  safe: '#2E7D32',          // Safe Status Green
  safeLight: '#E8F5E9',
  safeBorder: '#A5D6A7',

  warning: '#F57C00',       // Moderate Risk Amber
  warningLight: '#FFF3E0',
  warningBorder: '#FFE082',

  highRisk: '#D32F2F',      // High Risk Crimson
  highRiskLight: '#FFEBEE',
  highRiskBorder: '#EF9A9A',

  bg: '#F3F5F9',            // One UI Soft Canvas Background
  cardBg: '#FFFFFF',        // Card Surface
  cardBgSecondary: '#F8FAFC',

  textPrimary: '#111827',   // High-contrast primary text
  textSecondary: '#4B5563', // Subheadings & labels
  textMuted: '#94A3B8',     // Captions & timestamps
  textLight: '#FFFFFF',     // Inverse text on colored cards

  border: '#E2E8F0',
  divider: '#EEF2F6',

  // SOS Emergency Pulsing Glow
  sosRed: '#E53935',
  sosRedPulse: 'rgba(229, 57, 53, 0.25)',
  sosInnerGlow: '#B71C1C',

  shadowColor: '#0F172A',
};

export const typography = {
  headerTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: colors.textPrimary,
    letterSpacing: -0.5,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textPrimary,
    letterSpacing: -0.3,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  body: {
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  caption: {
    fontSize: 12,
    color: colors.textMuted,
  },
  badge: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  }
};

export const layout = {
  borderRadius: {
    sm: 12,
    md: 18,
    lg: 24,
    xl: 28,
    full: 9999,
  },
  padding: {
    xs: 6,
    sm: 10,
    md: 16,
    lg: 20,
    xl: 24,
  },
};

// Android / Material spacing + type scale used by the shared components
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  screen: 16, // horizontal screen padding
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  full: 9999,
};

export const fontSize = {
  title: 20,
  section: 16,
  body: 14,
  caption: 12,
};

export const touchTarget = 48;
