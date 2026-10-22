import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Linking, Alert } from 'react-native';
import { Screen, Card, SectionTitle, Button, ButtonRow, TextField } from '../components/ui';
import { useSafety } from '../context/SafetyContext';
import { sendEmergencySms } from '../../modules/surakshax-native';
import { spacing } from '../theme/colors';

export const ContactsScreen = ({ navigation }) => {
  const { guardians, updateGuardians } = useSafety();

  // Guardians load asynchronously from storage / server after login
  useEffect(() => {
    setName1(guardians[0]?.name || '');
    setPhone1(guardians[0]?.phone || '');
    setRelation1(guardians[0]?.relation || '');
    setName2(guardians[1]?.name || '');
    setPhone2(guardians[1]?.phone || '');
    setRelation2(guardians[1]?.relation || '');
  }, [guardians]);

  const [name1, setName1] = useState(guardians[0]?.name || '');
  const [phone1, setPhone1] = useState(guardians[0]?.phone || '');
  const [relation1, setRelation1] = useState(guardians[0]?.relation || '');

  const [name2, setName2] = useState(guardians[1]?.name || '');
  const [phone2, setPhone2] = useState(guardians[1]?.phone || '');
  const [relation2, setRelation2] = useState(guardians[1]?.relation || '');

  const [isSaving, setIsSaving] = useState(false);

  const handleCall = (phone) => {
    if (!phone || phone.trim().length === 0) {
      Alert.alert('Invalid Number', 'Please enter a valid phone number');
      return;
    }
    Linking.openURL(`tel:${phone.trim()}`).catch(() => {
      Alert.alert('Error', 'Unable to initiate phone call');
    });
  };

  const handleSave = async () => {
    if (!phone1.trim()) {
      Alert.alert('Missing Primary Phone', 'Please provide at least one emergency contact number');
      return;
    }

    setIsSaving(true);
    const newGuardians = [
      { id: '1', name: name1.trim() || 'Primary Guardian', phone: phone1.trim(), relation: relation1.trim() },
    ];
    if (phone2.trim()) {
      newGuardians.push({
        id: '2',
        name: name2.trim() || 'Secondary Guardian',
        phone: phone2.trim(),
        relation: relation2.trim(),
      });
    }

    await updateGuardians(newGuardians);
    setIsSaving(false);
    Alert.alert('Contacts saved', 'Your emergency contacts have been updated.');
  };

  const sendTestSms = (name, phone) => {
    const msg = `SurakshaX System Test: Hello ${name}, this is a test from your ward's SurakshaX Safety App. All automated systems active.`;
    if (!phone || !phone.trim()) {
      Alert.alert('Invalid Number', 'Please enter a phone number first');
      return;
    }
    sendEmergencySms([phone.trim()], msg)
      .then((res) => {
        const r = res && res[0];
        if (r && r.status === 'sent') Alert.alert('Test SMS Sent', `Test message sent to ${phone}.`);
        else if (r && r.status === 'failed') Alert.alert('SMS Failed', r.error || 'Unable to send SMS');
      })
      .catch(() => Alert.alert('Error', 'Cannot send SMS'));
  };

  return (
    <Screen title="Emergency contacts" onLeftPress={() => navigation.navigate('DashboardTab')}>
      <SectionTitle>Primary contact</SectionTitle>
      <ContactForm
        name={name1}
        setName={setName1}
        phone={phone1}
        setPhone={setPhone1}
        relation={relation1}
        setRelation={setRelation1}
        namePlaceholder="e.g. Mom"
        phonePlaceholder="e.g. 98765 43210"
        relationPlaceholder="e.g. Mother"
        onCall={() => handleCall(phone1)}
        onTestSms={() => sendTestSms(name1, phone1)}
      />

      <SectionTitle>Second contact</SectionTitle>
      <ContactForm
        name={name2}
        setName={setName2}
        phone={phone2}
        setPhone={setPhone2}
        relation={relation2}
        setRelation={setRelation2}
        namePlaceholder="e.g. Sister"
        phonePlaceholder="e.g. 91234 56789"
        relationPlaceholder="e.g. Friend"
        onCall={() => handleCall(phone2)}
        onTestSms={() => sendTestSms(name2, phone2)}
      />

      <Button title="Save contacts" icon="save" loading={isSaving} onPress={handleSave} />
    </Screen>
  );
};

const ContactForm = ({
  name,
  setName,
  phone,
  setPhone,
  relation,
  setRelation,
  namePlaceholder,
  phonePlaceholder,
  relationPlaceholder,
  onCall,
  onTestSms,
}) => (
  <Card>
    <TextField label="Name" value={name} onChangeText={setName} placeholder={namePlaceholder} />
    <TextField
      label="Phone number"
      value={phone}
      onChangeText={setPhone}
      keyboardType="phone-pad"
      placeholder={phonePlaceholder}
    />
    <TextField label="Relationship" value={relation} onChangeText={setRelation} placeholder={relationPlaceholder} />
    <ButtonRow style={styles.actions}>
      <Button title="Call" icon="call" variant="safe" onPress={onCall} />
      <Button title="Test SMS" icon="sms" variant="outline" onPress={onTestSms} />
    </ButtonRow>
  </Card>
);

const styles = StyleSheet.create({
  actions: { marginTop: spacing.xs },
});
