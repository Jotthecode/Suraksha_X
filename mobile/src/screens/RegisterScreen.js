// Sign-up wizard: Account -> About you -> Emergency contacts -> Review.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, StyleSheet, Pressable, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { usePreventRemove } from '@react-navigation/native';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafety } from '../context/SafetyContext';
import { PlaceSearchField } from '../components/PlaceSearchField';
import { DobField } from '../components/DobField';
import { Screen, Card, Button, ButtonRow, TextField, Chip, Notice } from '../components/ui';
import { colors, spacing, radius, fontSize, touchTarget } from '../theme/colors';
import {
  GENDERS,
  BLOOD_GROUPS,
  RELATIONS,
  isValidEmail,
  isValidPhone,
  phoneDigits,
  parseDob,
  formatDob,
} from '../utils/profileFields';

const STEPS = ['Account', 'About you', 'Contacts', 'Review'];
const MAX_CONTACTS = 5;

let contactSeq = 0;
const newContact = () => ({ id: `g${Date.now()}${contactSeq++}`, name: '', phone: '', relation: '' });

// ---------- validation (same rules as the server) ----------
const validateAccount = ({ name, email, password, confirm }) => {
  const e = {};
  if (!name.trim()) e.name = 'Enter your full name';
  if (!isValidEmail(email)) e.email = 'Enter a valid email address';
  if (password.length < 6) e.password = 'Use at least 6 characters';
  if (!e.password && confirm !== password) e.confirm = "Passwords don't match";
  return e;
};

const validateAbout = ({ phone, gender, bloodGroup, dob }) => {
  const e = {};
  if (!isValidPhone(phone)) e.phone = 'Enter your 10-digit mobile number';
  if (!GENDERS.includes(gender)) e.gender = 'Select your gender';
  if (!BLOOD_GROUPS.includes(bloodGroup)) e.bloodGroup = 'Select your blood group';
  const { error } = parseDob(dob);
  if (error) e.dob = error;
  return e;
};

const validateContacts = (contacts, ownPhone) => {
  const e = {};
  const own = phoneDigits(ownPhone);
  contacts.forEach((c, i) => {
    if (!c.name.trim()) e[`name${i}`] = 'Enter a name';
    if (!isValidPhone(c.phone)) e[`phone${i}`] = 'Enter a 10-digit mobile number';
    else if (phoneDigits(c.phone) === own) e[`phone${i}`] = "Can't be your own number";
  });
  return e;
};

const FieldError = ({ children }) => (children ? <Text style={styles.error}>{children}</Text> : null);

const PasswordField = ({ label, value, onChangeText, error, placeholder, autoComplete }) => {
  const [visible, setVisible] = useState(false);
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputRow, error && styles.inputError]}>
        <TextInput
          style={styles.inputFlex}
          value={value}
          onChangeText={onChangeText}
          secureTextEntry={!visible}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete={autoComplete}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
        />
        <Pressable
          onPress={() => setVisible((v) => !v)}
          hitSlop={8}
          style={styles.eyeBtn}
          accessibilityLabel={visible ? 'Hide password' : 'Show password'}
        >
          <MaterialIcons name={visible ? 'visibility-off' : 'visibility'} size={22} color={colors.textSecondary} />
        </Pressable>
      </View>
      <FieldError>{error}</FieldError>
    </View>
  );
};

/** TextField + inline error under it. */
const Field = ({ error, ...props }) => (
  <View style={styles.fieldWrap}>
    <TextField {...props} style={styles.noMargin} inputStyle={error ? styles.inputError : null} />
    <FieldError>{error}</FieldError>
  </View>
);

const PhoneField = ({ label, value, onChangeText, error, placeholder = '98765 43210' }) => (
  <View style={styles.fieldWrap}>
    <Text style={styles.label}>{label}</Text>
    <View style={[styles.inputRow, error && styles.inputError]}>
      <Text style={styles.prefix}>+91</Text>
      <View style={styles.prefixDivider} />
      <TextInput
        style={styles.inputFlex}
        value={value}
        onChangeText={(t) => onChangeText(t.replace(/[^\d+ ]/g, ''))}
        keyboardType="phone-pad"
        autoComplete="tel"
        maxLength={14}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
      />
    </View>
    <FieldError>{error}</FieldError>
  </View>
);

const StepIndicator = ({ step }) => (
  <View style={styles.stepper}>
    <View style={styles.stepperTop}>
      <Text style={styles.stepCount}>
        Step {step + 1} of {STEPS.length}
      </Text>
      <Text style={styles.stepName}>{STEPS[step]}</Text>
    </View>
    <View style={styles.progressRow}>
      {STEPS.map((s, i) => (
        <View key={s} style={[styles.progressSeg, i > 0 && styles.progressGap, i <= step && styles.progressOn]} />
      ))}
    </View>
  </View>
);

const ReviewRow = ({ label, value }) => (
  <View style={styles.reviewRow}>
    <Text style={styles.reviewLabel}>{label}</Text>
    <Text style={styles.reviewValue}>{value || '—'}</Text>
  </View>
);

const ReviewCard = ({ title, onEdit, children }) => (
  <Card>
    <View style={styles.reviewHeader}>
      <Text style={styles.cardTitle}>{title}</Text>
      <Pressable onPress={onEdit} hitSlop={8} style={styles.editBtn} accessibilityRole="button">
        <Text style={styles.link}>Edit</Text>
      </Pressable>
    </View>
    {children}
  </Card>
);

export const RegisterScreen = ({ navigation }) => {
  const { registerUser, currentLocation } = useSafety();
  const insets = useSafeAreaInsets();
  const scrollRef = useRef(null);

  const [step, setStep] = useState(0);
  const [showErrors, setShowErrors] = useState([false, false, false]);

  // Step 1
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  // Step 2
  const [phone, setPhone] = useState('');
  const [gender, setGender] = useState('');
  const [bloodGroup, setBloodGroup] = useState('');
  const [dob, setDob] = useState({ day: '', month: '', year: '' });
  const [address, setAddress] = useState('');
  const [medicalNotes, setMedicalNotes] = useState('');
  // Step 3
  const [contacts, setContacts] = useState(() => [newContact()]);
  // Submit
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const errorsByStep = [
    validateAccount({ name, email, password, confirm }),
    validateAbout({ phone, gender, bloodGroup, dob }),
    validateContacts(contacts, phone),
  ];
  const visibleErrors = errorsByStep.map((e, i) => (showErrors[i] ? e : {}));

  useEffect(() => {
    scrollRef.current?.scrollTo?.({ y: 0, animated: false });
  }, [step]);

  const goToLogin = () => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Login'));
  const prevStep = () => (step > 0 ? setStep(step - 1) : goToLogin());

  // Android hardware back / swipe goes to the previous step instead of leaving the wizard
  usePreventRemove(step > 0 && !isLoading, () => setStep((s) => Math.max(0, s - 1)));

  const nextStep = () => {
    const errs = errorsByStep[step];
    if (Object.keys(errs).length > 0) {
      setShowErrors((prev) => prev.map((v, i) => (i === step ? true : v)));
      return;
    }
    setStep(step + 1);
  };

  const jumpTo = (target) => {
    setServerError('');
    setStep(target);
  };

  const updateContact = (index, patch) =>
    setContacts((list) => list.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  const addContact = () => setContacts((list) => (list.length < MAX_CONTACTS ? [...list, newContact()] : list));
  const removeContact = (index) => setContacts((list) => list.filter((_, i) => i !== index));

  const handleCreate = async () => {
    // Re-check everything in case something was edited from the review step
    const firstBad = errorsByStep.findIndex((e) => Object.keys(e).length > 0);
    if (firstBad >= 0) {
      setShowErrors([true, true, true]);
      setStep(firstBad);
      return;
    }
    setServerError('');
    setIsLoading(true);
    const res = await registerUser({
      email: email.trim().toLowerCase(),
      password,
      name: name.trim(),
      phone: phoneDigits(phone),
      gender,
      blood_group: bloodGroup,
      date_of_birth: parseDob(dob).value,
      address: address.trim(),
      medical_notes: medicalNotes.trim(),
      guardians: contacts.map((c) => ({
        id: c.id,
        name: c.name.trim(),
        phone: phoneDigits(c.phone),
        relation: c.relation || 'Other',
      })),
    });
    // On success the context logs in and the navigator swaps to the app; nothing else to do here
    if (!res.success) {
      setIsLoading(false);
      setServerError(res.error || 'Could not create your account. Try again.');
    }
  };

  const near = currentLocation?.isRealGps ? { lat: currentLocation.latitude, lon: currentLocation.longitude } : undefined;

  const renderAccount = () => {
    const e = visibleErrors[0];
    return (
      <Card>
        <Field
          label="Full name"
          value={name}
          onChangeText={setName}
          placeholder="Your name"
          autoComplete="name"
          autoCapitalize="words"
          error={e.name}
        />
        <Field
          label="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="email"
          placeholder="you@example.com"
          error={e.email}
        />
        <PasswordField
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="At least 6 characters"
          autoComplete="new-password"
          error={e.password}
        />
        <PasswordField
          label="Confirm password"
          value={confirm}
          onChangeText={setConfirm}
          placeholder="Re-enter password"
          autoComplete="new-password"
          error={e.confirm}
        />
      </Card>
    );
  };

  const renderAbout = () => {
    const e = visibleErrors[1];
    return (
      <Card>
        <PhoneField label="Mobile number" value={phone} onChangeText={setPhone} error={e.phone} />

        <View style={styles.fieldWrap}>
          <Text style={styles.label}>Gender</Text>
          <View style={styles.chips}>
            {GENDERS.map((g) => (
              <Chip key={g} label={g} selected={gender === g} onPress={() => setGender(g)} />
            ))}
          </View>
          <FieldError>{e.gender}</FieldError>
        </View>

        <View style={styles.fieldWrap}>
          <Text style={styles.label}>Blood group</Text>
          <View style={styles.bloodGrid}>
            {BLOOD_GROUPS.map((b) => {
              const selected = bloodGroup === b;
              return (
                <Pressable
                  key={b}
                  onPress={() => setBloodGroup(b)}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                  style={[styles.bloodCell, selected && styles.bloodCellOn]}
                >
                  <Text style={[styles.bloodText, selected && styles.bloodTextOn]}>{b}</Text>
                </Pressable>
              );
            })}
          </View>
          <FieldError>{e.bloodGroup}</FieldError>
        </View>

        <DobField value={dob} onChange={setDob} error={e.dob} />

        <PlaceSearchField
          label="Home address (optional)"
          value={address}
          onChangeText={setAddress}
          onSelect={(p) => setAddress(p.subtitle ? `${p.name}, ${p.subtitle}` : p.name)}
          near={near}
          placeholder="Search your area or street"
        />

        <TextField
          label="Medical notes (optional)"
          value={medicalNotes}
          onChangeText={setMedicalNotes}
          placeholder="Allergies, conditions, medicines"
          multiline
          textAlignVertical="top"
          inputStyle={styles.multiline}
          style={styles.noMargin}
        />
      </Card>
    );
  };

  const renderContacts = () => {
    const e = visibleErrors[2];
    return (
      <>
        <Text style={styles.intro}>We'll alert them when you send an SOS.</Text>
        {contacts.map((c, i) => (
          <Card key={c.id}>
            <View style={styles.contactHeader}>
              <Text style={styles.cardTitle}>{i === 0 ? 'Primary contact' : `Contact ${i + 1}`}</Text>
              {i > 0 ? (
                <Pressable
                  onPress={() => removeContact(i)}
                  hitSlop={8}
                  style={styles.removeBtn}
                  accessibilityLabel={`Remove contact ${i + 1}`}
                >
                  <MaterialIcons name="delete-outline" size={22} color={colors.textSecondary} />
                </Pressable>
              ) : null}
            </View>
            <Field
              label="Name"
              value={c.name}
              onChangeText={(t) => updateContact(i, { name: t })}
              placeholder="Contact name"
              autoCapitalize="words"
              error={e[`name${i}`]}
            />
            <PhoneField
              label="Mobile number"
              value={c.phone}
              onChangeText={(t) => updateContact(i, { phone: t })}
              placeholder="98765 00001"
              error={e[`phone${i}`]}
            />
            <Text style={styles.label}>Relation</Text>
            <View style={[styles.chips, styles.chipsLast]}>
              {RELATIONS.map((r) => (
                <Chip
                  key={r}
                  label={r}
                  selected={c.relation === r}
                  onPress={() => updateContact(i, { relation: c.relation === r ? '' : r })}
                />
              ))}
            </View>
          </Card>
        ))}
        {contacts.length < MAX_CONTACTS ? (
          <Button title="Add another contact" icon="person-add" variant="outline" onPress={addContact} />
        ) : null}
      </>
    );
  };

  const renderReview = () => (
    <>
      {serverError ? (
        <Notice tone="danger" icon="error-outline">
          {serverError}
        </Notice>
      ) : null}
      <ReviewCard title="Account" onEdit={() => jumpTo(0)}>
        <ReviewRow label="Name" value={name.trim()} />
        <ReviewRow label="Email" value={email.trim().toLowerCase()} />
        <ReviewRow label="Password" value={'•'.repeat(Math.min(password.length, 12))} />
      </ReviewCard>
      <ReviewCard title="About you" onEdit={() => jumpTo(1)}>
        <ReviewRow label="Mobile" value={`+91 ${phoneDigits(phone)}`} />
        <ReviewRow label="Gender" value={gender} />
        <ReviewRow label="Blood group" value={bloodGroup} />
        <ReviewRow label="Date of birth" value={formatDob(parseDob(dob).value)} />
        <ReviewRow label="Address" value={address.trim()} />
        <ReviewRow label="Medical notes" value={medicalNotes.trim()} />
      </ReviewCard>
      <ReviewCard title="Emergency contacts" onEdit={() => jumpTo(2)}>
        {contacts.map((c) => (
          <ReviewRow
            key={c.id}
            label={c.relation || 'Contact'}
            value={`${c.name.trim()}  ·  +91 ${phoneDigits(c.phone)}`}
          />
        ))}
      </ReviewCard>
    </>
  );

  const isLast = step === STEPS.length - 1;

  return (
    <Screen title="Create account" onLeftPress={prevStep} scroll={false}>
      <StepIndicator step={step} />
      <ScrollView
        ref={scrollRef}
        style={styles.flex}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {step === 0 && renderAccount()}
        {step === 1 && renderAbout()}
        {step === 2 && renderContacts()}
        {step === 3 && renderReview()}

        {step === 0 ? (
          <View style={styles.loginRow}>
            <Text style={styles.promptText}>Already have an account?</Text>
            <Pressable onPress={goToLogin} hitSlop={12} style={styles.linkBtn}>
              <Text style={styles.link}>Sign in</Text>
            </Pressable>
          </View>
        ) : null}
      </ScrollView>

      <View style={[styles.bottomBar, { paddingBottom: spacing.sm + insets.bottom }]}>
        <ButtonRow>
          {step > 0 ? <Button title="Back" variant="outline" onPress={prevStep} disabled={isLoading} /> : null}
          {isLast ? (
            <Button title="Create account" loading={isLoading} onPress={handleCreate} />
          ) : (
            <Button title="Next" onPress={nextStep} />
          )}
        </ButtonRow>
      </View>
    </Screen>
  );
};


const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingHorizontal: spacing.screen, paddingTop: spacing.md, paddingBottom: spacing.lg },
  stepper: {
    backgroundColor: colors.cardBg,
    paddingHorizontal: spacing.screen,
    paddingTop: 12,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  stepperTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  stepCount: { fontSize: fontSize.caption, fontWeight: '600', color: colors.textSecondary },
  stepName: { fontSize: fontSize.body, fontWeight: '600', color: colors.textPrimary },
  progressRow: { flexDirection: 'row' },
  progressSeg: { flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.border },
  progressGap: { marginLeft: spacing.xs },
  progressOn: { backgroundColor: colors.primary },
  fieldWrap: { marginBottom: spacing.md },
  noMargin: { marginBottom: 0 },
  label: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  error: { fontSize: fontSize.caption, color: colors.primary, marginTop: spacing.xs },
  inputRow: {
    minHeight: touchTarget,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingLeft: spacing.md,
  },
  inputFlex: {
    flex: 1,
    minHeight: touchTarget - 2,
    fontSize: fontSize.body,
    color: colors.textPrimary,
    paddingVertical: spacing.sm,
    paddingRight: spacing.md,
  },
  inputError: { borderColor: colors.primary },
  eyeBtn: { width: touchTarget, height: touchTarget - 2, alignItems: 'center', justifyContent: 'center' },
  prefix: { fontSize: fontSize.body, fontWeight: '600', color: colors.textPrimary },
  prefixDivider: { width: 1, height: 24, backgroundColor: colors.border, marginHorizontal: 12 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: -spacing.sm },
  chipsLast: { marginBottom: -spacing.sm },
  bloodGrid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -spacing.xs },
  bloodCell: {
    width: '25%',
    paddingHorizontal: spacing.xs,
    marginBottom: spacing.sm,
  },
  bloodCellOn: {},
  bloodText: {
    minHeight: 44,
    lineHeight: 42,
    textAlign: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.cardBg,
    fontSize: fontSize.body,
    fontWeight: '600',
    color: colors.textSecondary,
    overflow: 'hidden',
  },
  bloodTextOn: { backgroundColor: colors.primaryLight, borderColor: colors.primary, color: colors.primaryDark },
  multiline: { minHeight: 88, paddingTop: 12 },
  intro: { fontSize: fontSize.body, color: colors.textSecondary, marginBottom: 12 },
  cardTitle: { fontSize: fontSize.section, fontWeight: '600', color: colors.textPrimary },
  contactHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 32,
    marginBottom: 12,
  },
  removeBtn: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center', marginRight: -spacing.sm },
  reviewHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.xs },
  editBtn: { minHeight: 40, minWidth: 48, alignItems: 'flex-end', justifyContent: 'center' },
  reviewRow: {
    flexDirection: 'row',
    paddingVertical: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  reviewLabel: { width: 112, fontSize: fontSize.body, color: colors.textSecondary },
  reviewValue: { flex: 1, fontSize: fontSize.body, color: colors.textPrimary },
  bottomBar: {
    backgroundColor: colors.cardBg,
    paddingHorizontal: spacing.screen,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  loginRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: spacing.xs },
  promptText: { fontSize: fontSize.body, color: colors.textSecondary },
  linkBtn: { minHeight: 40, justifyContent: 'center', paddingHorizontal: spacing.xs },
  link: { fontSize: fontSize.body, fontWeight: '600', color: colors.primary },
});
