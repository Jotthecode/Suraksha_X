import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { Screen, Card, SectionTitle, Button, ButtonRow, TextField, Chip, ListRow, Notice } from '../components/ui';
import { useSafety } from '../context/SafetyContext';
import { getBaseUrl, setBaseUrl, DEFAULT_HOST, CLOUD_HOST } from '../api/config';
import { PlaceSearchField } from '../components/PlaceSearchField';
import { DobField } from '../components/DobField';
import { colors, spacing, fontSize } from '../theme/colors';
import { GENDERS, BLOOD_GROUPS, isValidPhone, phoneDigits, splitDob, parseDob } from '../utils/profileFields';
import appJson from '../../app.json';

export const ProfileScreen = ({ navigation }) => {
  const { user, updateUserProfile, logoutUser, currentLocation } = useSafety();

  const [name, setName] = useState(user.name || '');
  const [email, setEmail] = useState(user.email || '');
  const [phone, setPhone] = useState(user.phone || '');
  const [gender, setGender] = useState(user.gender || '');
  const [bloodGroup, setBloodGroup] = useState(user.bloodGroup || user.blood_group || '');
  const [dob, setDob] = useState(() => splitDob(user.date_of_birth));
  const [address, setAddress] = useState(user.address || '');
  const [medicalNotes, setMedicalNotes] = useState(user.medical_notes || '');
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const near = currentLocation?.isRealGps ? { lat: currentLocation.latitude, lon: currentLocation.longitude } : undefined;

  const [serverUrl, setServerUrlState] = useState(DEFAULT_HOST);
  const [isTestingServer, setIsTestingServer] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);

  useEffect(() => {
    loadServerUrl();
  }, []);

  const loadServerUrl = async () => {
    const url = await getBaseUrl();
    setServerUrlState(url);
  };

  const handleSaveProfile = async () => {
    const nextErrors = {};
    if (!name.trim()) nextErrors.name = 'Enter your full name';
    if (!isValidPhone(phone)) nextErrors.phone = 'Enter your 10-digit mobile number';
    const parsedDob = parseDob(dob);
    if (parsedDob.error) nextErrors.dob = parsedDob.error;
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setIsSaving(true);
    await updateUserProfile({
      name: name.trim(),
      email: email.trim(),
      phone: phoneDigits(phone),
      gender,
      bloodGroup,
      date_of_birth: parsedDob.value,
      address: address.trim(),
      medical_notes: medicalNotes.trim(),
    });
    setIsSaving(false);
    Alert.alert('Profile saved', 'Your details have been updated.');
  };

  const handleSaveServerUrl = async (urlToSave) => {
    const finalUrl = urlToSave || serverUrl;
    await setBaseUrl(finalUrl);
    setServerUrlState(finalUrl);
    Alert.alert('Server updated', `Server set to:\n${finalUrl}`);
  };

  const testServerConnection = async () => {
    setIsTestingServer(true);
    setServerStatus(null);
    try {
      const res = await fetch(`${serverUrl.replace(/\/+$/, '')}/?format=json`, {
        headers: { Accept: 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        setServerStatus({
          online: true,
          service: data.service || 'SurakshaX Backend',
          version: data.version || '2.0',
        });
      } else {
        setServerStatus({ online: false, error: `HTTP ${res.status}` });
      }
    } catch (e) {
      setServerStatus({ online: false, error: e.message });
    } finally {
      setIsTestingServer(false);
    }
  };

  const choosePreset = (url) => {
    setServerUrlState(url);
    handleSaveServerUrl(url);
  };

  const confirmLogout = () =>
    Alert.alert('Log out?', 'Your contacts and SOS history stay on this phone.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logoutUser },
    ]);

  return (
    <Screen title="Settings" onLeftPress={() => navigation.goBack()} bottomInset>
      <SectionTitle>Profile</SectionTitle>
      <Card>
        <TextField
          label="Full name"
          value={name}
          onChangeText={setName}
          style={errors.name ? styles.fieldWithError : null}
          inputStyle={errors.name ? styles.inputError : null}
        />
        {errors.name ? <Text style={styles.error}>{errors.name}</Text> : null}
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <TextField
          label="Mobile number"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          placeholder="10-digit number"
          style={errors.phone ? styles.fieldWithError : null}
          inputStyle={errors.phone ? styles.inputError : null}
        />
        {errors.phone ? <Text style={styles.error}>{errors.phone}</Text> : null}

        <Text style={styles.label}>Gender</Text>
        <View style={styles.chips}>
          {GENDERS.map((g) => (
            <Chip key={g} label={g} selected={gender === g} onPress={() => setGender(g)} />
          ))}
        </View>

        <Text style={styles.label}>Blood group</Text>
        <View style={styles.chips}>
          {BLOOD_GROUPS.map((b) => (
            <Chip key={b} label={b} selected={bloodGroup === b} onPress={() => setBloodGroup(b)} />
          ))}
        </View>

        <DobField label="Date of birth" value={dob} onChange={setDob} error={errors.dob} />

        <PlaceSearchField
          label="Home address"
          value={address}
          onChangeText={setAddress}
          onSelect={(p) => setAddress(p.subtitle ? `${p.name}, ${p.subtitle}` : p.name)}
          near={near}
          placeholder="Search your area or street"
        />

        <TextField
          label="Medical notes"
          value={medicalNotes}
          onChangeText={setMedicalNotes}
          placeholder="Allergies, conditions, medicines"
          multiline
          textAlignVertical="top"
          inputStyle={styles.multiline}
        />
        <Button title="Save profile" icon="save" loading={isSaving} onPress={handleSaveProfile} />
      </Card>

      <SectionTitle>Server</SectionTitle>
      <Card>
        <View style={styles.chips}>
          <Chip label="Android emulator" icon="phone-android" onPress={() => choosePreset('http://10.0.2.2:5000')} selected={serverUrl === 'http://10.0.2.2:5000'} />
          <Chip label="Localhost" icon="computer" onPress={() => choosePreset('http://localhost:5000')} selected={serverUrl === 'http://localhost:5000'} />
          <Chip label="Cloud" icon="cloud" onPress={() => choosePreset(CLOUD_HOST)} selected={serverUrl === CLOUD_HOST} />
        </View>
        <TextField
          label="Server URL"
          value={serverUrl}
          onChangeText={setServerUrlState}
          placeholder="http://192.168.x.x:5000"
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
        <ButtonRow>
          <Button title="Save" variant="accent" onPress={() => handleSaveServerUrl()} />
          <Button title="Test connection" variant="outline" loading={isTestingServer} onPress={testServerConnection} />
        </ButtonRow>

        {serverStatus && (
          <Notice
            tone={serverStatus.online ? 'safe' : 'danger'}
            icon={serverStatus.online ? 'check-circle' : 'error-outline'}
            style={styles.status}
          >
            {serverStatus.online
              ? `Connected: ${serverStatus.service} (v${serverStatus.version})`
              : `Can't connect: ${serverStatus.error}`}
          </Notice>
        )}
      </Card>

      <SectionTitle>Account</SectionTitle>
      <Card padded={false}>
        <ListRow icon="tour" label="App tour" onPress={() => navigation.navigate('Walkthrough', { replay: true })} />
        <ListRow icon="logout" label="Log out" danger onPress={confirmLogout} chevron={false} divider />
      </Card>

      <Text style={styles.version}>SurakshaX {appJson?.expo?.version}</Text>
    </Screen>
  );
};

const styles = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.sm },
  label: { fontSize: fontSize.caption, fontWeight: '500', color: colors.textSecondary, marginBottom: spacing.xs },
  error: { fontSize: fontSize.caption, color: colors.primary, marginTop: spacing.xs, marginBottom: spacing.md },
  fieldWithError: { marginBottom: 0 },
  inputError: { borderColor: colors.primary },
  multiline: { minHeight: 88, paddingTop: 12 },
  status: { marginTop: spacing.md, marginBottom: 0 },
  version: { fontSize: fontSize.caption, color: colors.textMuted, textAlign: 'center', marginTop: spacing.sm },
});
