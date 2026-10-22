import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Pressable, Alert, Platform } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  useAudioRecorder,
  createAudioPlayer,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  RecordingPresets,
} from 'expo-audio';
import { colors, spacing, radius, fontSize } from '../theme/colors';
import { Screen, Card, SectionTitle, Button, EmptyState } from '../components/ui';

const STORAGE_RECORDINGS_KEY = 'surakshax_audio_recordings_list';

export const RecordingsScreen = ({ navigation }) => {
  const [recordings, setRecordings] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [playingId, setPlayingId] = useState(null);

  // Web MediaRecorder references
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);
  const currentAudioElementRef = useRef(null);

  // Native recorder (saved to the app's document directory so evidence isn't purged with the cache)
  const nativeRecorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, directory: 'document' });
  const isNativeRecordingRef = useRef(false);
  const expoSoundRef = useRef(null);
  const durationRef = useRef(0);

  useEffect(() => {
    loadSavedRecordings();

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (currentAudioElementRef.current) {
        currentAudioElementRef.current.pause();
      }
      if (expoSoundRef.current) {
        try { expoSoundRef.current.remove(); } catch (e) {}
      }
    };
  }, []);

  const loadSavedRecordings = async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_RECORDINGS_KEY);
      if (stored) {
        setRecordings(JSON.parse(stored));
      } else {
        setRecordings([]);
      }
    } catch (e) {
      console.warn('Failed to load recordings:', e);
    }
  };

  const saveRecordingsList = async (list) => {
    setRecordings(list);
    try {
      await AsyncStorage.setItem(STORAGE_RECORDINGS_KEY, JSON.stringify(list));
    } catch (e) {
      console.warn('Failed to save recordings:', e);
    }
  };

  // 1. START RECORDING
  const startRecording = async () => {
    try {
      if (playingId) stopPlayback();

      if (Platform.OS === 'web' && typeof navigator !== 'undefined' && navigator.mediaDevices) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunksRef.current = [];

        const recorder = new MediaRecorder(stream);
        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        recorder.onstop = () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const audioUrl = URL.createObjectURL(audioBlob);
          handleRecordingFinished(audioUrl);

          // Stop all stream tracks
          stream.getTracks().forEach((track) => track.stop());
        };

        recorder.start(100);
        mediaRecorderRef.current = recorder;
      } else {
        const permission = await requestRecordingPermissionsAsync();
        if (!permission.granted) {
          Alert.alert('Permission Denied', 'Microphone permission is required to record audio evidence.');
          return;
        }

        await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
        await nativeRecorder.prepareToRecordAsync();
        nativeRecorder.record();
        isNativeRecordingRef.current = true;
      }

      setIsRecording(true);
      setRecordingDuration(0);
      durationRef.current = 0;

      timerIntervalRef.current = setInterval(() => {
        durationRef.current += 1;
        setRecordingDuration(durationRef.current);
      }, 1000);
    } catch (err) {
      console.error('Cannot start recording:', err);
      Alert.alert('Microphone Error', `Unable to access microphone: ${err.message}`);
      setIsRecording(false);
    }
  };

  // 2. STOP RECORDING
  const stopRecording = async () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    setIsRecording(false);

    if (Platform.OS === 'web' && mediaRecorderRef.current) {
      try {
        if (mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
      } catch (e) {}
    } else if (isNativeRecordingRef.current) {
      try {
        isNativeRecordingRef.current = false;
        await nativeRecorder.stop();
        await setAudioModeAsync({ allowsRecording: false });
        handleRecordingFinished(nativeRecorder.uri);
      } catch (e) {
        console.warn('Error stopping Expo recording:', e);
      }
    }
  };

  const handleRecordingFinished = (audioUri) => {
    const now = new Date();
    const newEntry = {
      id: 'REC-' + Math.floor(1000 + Math.random() * 9000),
      title: `Recording ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      date_str:
        now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) +
        ', ' +
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      duration_seconds: Math.max(durationRef.current, 1),
      trigger_type: 'Manual Evidence Recording',
      audio_url: audioUri,
    };

    setRecordings((prev) => {
      const updated = [newEntry, ...prev];
      AsyncStorage.setItem(STORAGE_RECORDINGS_KEY, JSON.stringify(updated)).catch(() => {});
      return updated;
    });
  };

  // 3. PLAYBACK
  const togglePlay = async (record) => {
    if (playingId === record.id) {
      stopPlayback();
      return;
    }

    stopPlayback();

    if (!record.audio_url) {
      Alert.alert(
        'Sample Evidence Recording',
        `This is a metadata incident record (${record.title}). Newly captured clips from the mic above can be listened to in full!`
      );
      return;
    }

    if (Platform.OS === 'web') {
      const audio = new window.Audio(record.audio_url);
      audio.onended = () => {
        setPlayingId(null);
      };
      audio.onerror = () => {
        setPlayingId(null);
        Alert.alert('Playback Error', 'Unable to play this audio stream.');
      };
      audio.play();
      currentAudioElementRef.current = audio;
      setPlayingId(record.id);
    } else {
      try {
        await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
        const player = createAudioPlayer({ uri: record.audio_url });
        expoSoundRef.current = player;
        player.addListener('playbackStatusUpdate', (status) => {
          if (status.didJustFinish) {
            setPlayingId(null);
          }
        });
        player.play();
        setPlayingId(record.id);
      } catch (e) {
        Alert.alert('Playback Error', 'Cannot play audio on this device.');
      }
    }
  };

  const stopPlayback = () => {
    if (currentAudioElementRef.current) {
      try {
        currentAudioElementRef.current.pause();
        currentAudioElementRef.current.currentTime = 0;
      } catch (e) {}
      currentAudioElementRef.current = null;
    }
    if (expoSoundRef.current) {
      try {
        expoSoundRef.current.pause();
        expoSoundRef.current.remove();
      } catch (e) {}
      expoSoundRef.current = null;
    }
    setPlayingId(null);
  };

  // 4. DELETE
  const handleDelete = (id) => {
    Alert.alert(
      'Delete Recording',
      'Are you sure you want to permanently delete this audio evidence recording?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            if (playingId === id) stopPlayback();
            const updated = recordings.filter((r) => r.id !== id);
            saveRecordingsList(updated);
          },
        },
      ]
    );
  };

  const formatSeconds = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <Screen title="Recordings" onLeftPress={() => navigation.goBack()} bottomInset>
      <Card>
        <View style={styles.recorderRow}>
          <View style={[styles.recDot, isRecording && styles.recDotActive]} />
          <Text style={styles.timer}>{formatSeconds(recordingDuration)}</Text>
          <Text style={styles.recState}>{isRecording ? 'Recording…' : 'Ready'}</Text>
        </View>
        <Button
          title={isRecording ? 'Stop and save' : 'Start recording'}
          icon={isRecording ? 'stop' : 'mic'}
          variant={isRecording ? 'dark' : 'primary'}
          onPress={isRecording ? stopRecording : startRecording}
        />
      </Card>

      <SectionTitle right={<Text style={styles.count}>{recordings.length}</Text>}>Saved recordings</SectionTitle>

      {recordings.length === 0 ? (
        <EmptyState icon="mic-none" title="No recordings yet" message="Recordings are saved privately on this phone." />
      ) : (
        <Card padded={false}>
          {recordings.map((item, idx) => {
            const isPlaying = playingId === item.id;
            const isSos = (item.trigger_type || '').includes('SOS');
            return (
              <View key={item.id} style={[styles.recRow, idx > 0 && styles.recRowDivider]}>
                <Pressable
                  onPress={() => togglePlay(item)}
                  accessibilityLabel={isPlaying ? 'Pause' : 'Play'}
                  android_ripple={{ color: colors.divider, borderless: true, radius: 24 }}
                  style={[styles.playBtn, isPlaying && styles.playBtnActive]}
                >
                  <MaterialIcons
                    name={isPlaying ? 'pause' : 'play-arrow'}
                    size={26}
                    color={isPlaying ? colors.textLight : colors.primary}
                  />
                </Pressable>
                <View style={styles.recInfo}>
                  <Text style={styles.recTitle} numberOfLines={1}>
                    {item.title}
                  </Text>
                  <Text style={styles.recMeta} numberOfLines={1}>
                    {item.date_str}
                    {isSos ? '  ·  SOS' : ''}
                  </Text>
                </View>
                <Text style={styles.duration}>{formatSeconds(item.duration_seconds)}</Text>
                <Pressable
                  onPress={() => handleDelete(item.id)}
                  accessibilityLabel="Delete recording"
                  android_ripple={{ color: colors.divider, borderless: true, radius: 24 }}
                  style={styles.iconBtn}
                >
                  <MaterialIcons name="delete-outline" size={22} color={colors.textSecondary} />
                </Pressable>
              </View>
            );
          })}
        </Card>
      )}
    </Screen>
  );
};

const styles = StyleSheet.create({
  recorderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.md },
  recDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.border },
  recDotActive: { backgroundColor: colors.sosRed },
  timer: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textPrimary,
    marginLeft: 12,
    fontVariant: ['tabular-nums'],
  },
  recState: { marginLeft: 'auto', fontSize: fontSize.body, color: colors.textSecondary },
  count: { fontSize: fontSize.body, color: colors.textSecondary },
  recRow: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: spacing.md,
    paddingRight: spacing.xs,
    paddingVertical: spacing.sm,
  },
  recRowDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  playBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playBtnActive: { backgroundColor: colors.primary },
  recInfo: { flex: 1, marginLeft: 12 },
  recTitle: { fontSize: fontSize.body, fontWeight: '500', color: colors.textPrimary },
  recMeta: { fontSize: fontSize.caption, color: colors.textSecondary, marginTop: 2 },
  duration: { fontSize: fontSize.caption, color: colors.textSecondary, marginLeft: spacing.sm, fontVariant: ['tabular-nums'] },
  iconBtn: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center' },
});
