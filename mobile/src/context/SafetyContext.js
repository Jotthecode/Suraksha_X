import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import {
  predictCrimeRisk,
  dispatchEmergencyAlert,
  getNearestPoliceStations,
  getLiveTrackingUrl,
  streamGpsUpdate,
  apiLogin,
  apiRegister,
  apiGetProfile,
  apiUpdateGuardians,
  apiUpdateProfile,
  reverseGeocode,
  saveAuthToken,
  warmUpBackend,
} from '../api/config';
import { sendEmergencySms, requestEmergencyPermissions, placeEmergencyCall } from '../../modules/surakshax-native';
import { getLocationQuietly } from '../utils/location';

export const SafetyContext = createContext();

const STORAGE_KEYS = {
  USER: 'surakshax_user_profile',
  GUARDIANS: 'surakshax_guardians',
  INCIDENTS: 'surakshax_incidents_history',
};

const EMPTY_USER = { name: '', email: '', phone: '', gender: 'Female', bloodGroup: 'O+' };

const randomSessionId = () => {
  const chars = 'abcdef0123456789';
  let id = '';
  for (let i = 0; i < 32; i++) id += chars[Math.floor(Math.random() * chars.length)];
  return id;
};

export const SafetyProvider = ({ children }) => {
  const [isAuthLoaded, setIsAuthLoaded] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(EMPTY_USER);
  const [guardians, setGuardians] = useState([]);

  const [currentLocation, setCurrentLocation] = useState({
    // Placeholder until the first GPS fix (geographic centre of India); never used for SOS
    latitude: 22.9734,
    longitude: 78.6569,
    address: 'Locating…',
    isRealGps: false,
  });
  const locationRef = useRef(currentLocation);
  useEffect(() => {
    locationRef.current = currentLocation;
  }, [currentLocation]);

  const [riskData, setRiskData] = useState({ category: 'Checking…', risk_score: 0, factors: {} });

  const [incidents, setIncidents] = useState([]);
  const [isRefreshingLocation, setIsRefreshingLocation] = useState(false);
  const [isSOSActive, setIsSOSActive] = useState(false);
  const [sosReason, setSosReason] = useState('Manual SOS Button');

  // Emergency tracking session that keeps streaming after an SOS dispatch
  const emergencyStreamRef = useRef(null);

  // 1. Initial Load from AsyncStorage
  useEffect(() => {
    warmUpBackend();
    loadStoredData();
    detectDeviceLocation();
    if (Platform.OS === 'android') requestEmergencyPermissions();
    return () => {
      emergencyStreamRef.current?.remove?.();
    };
  }, []);

  const loadStoredData = async () => {
    try {
      const storedUser = await AsyncStorage.getItem(STORAGE_KEYS.USER);
      if (storedUser) {
        setUser({ ...EMPTY_USER, ...JSON.parse(storedUser) });
        setIsLoggedIn(true);
        // A login from another server (or an expired one) is rejected with 401: sign out so the user logs in again.
        // Offline or server errors keep the local session, so SOS keeps working without internet.
        apiGetProfile()
          .then((res) => {
            if (res && res.status === 401) logoutUser();
          })
          .catch(() => {});
      }

      const storedGuardians = await AsyncStorage.getItem(STORAGE_KEYS.GUARDIANS);
      if (storedGuardians) setGuardians(JSON.parse(storedGuardians));

      const storedIncidents = await AsyncStorage.getItem(STORAGE_KEYS.INCIDENTS);
      if (storedIncidents) setIncidents(JSON.parse(storedIncidents));
    } catch (e) {
      console.warn('Failed to load local storage:', e);
    } finally {
      setIsAuthLoaded(true);
    }
  };

  // 2. Real GPS Location Detection (Device & Web Browser)
  const detectDeviceLocation = async () => {
    setIsRefreshingLocation(true);

    if (Platform.OS === 'web' && typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          setCurrentLocation({
            latitude: lat,
            longitude: lon,
            address: `GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}`,
            isRealGps: true,
          });
          describeLocation(lat, lon).then((address) =>
            setCurrentLocation((prev) => (prev.latitude === lat && prev.longitude === lon ? { ...prev, address } : prev))
          );
          await fetchRiskForCoords(lat, lon);
          setIsRefreshingLocation(false);
        },
        async () => {
          await fallbackExpoLocation();
        },
        { timeout: 8000, enableHighAccuracy: true }
      );
      return;
    }

    await fallbackExpoLocation();
  };

  // Street-level label for a coordinate: free OpenStreetMap lookup on the server (no API key),
  // then the phone's own geocoder on Android/iOS (web has none), then raw coordinates
  const describeLocation = async (lat, lon) => {
    try {
      const label = await reverseGeocode(lat, lon);
      if (label) return label;
    } catch (e) {}
    if (Platform.OS !== 'web') {
      try {
        const [place] = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lon });
        const label = place && [place.name, place.district || place.subregion, place.city].filter(Boolean).join(', ');
        if (label) return label;
      } catch (e) {}
    }
    return `GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
  };

  const fallbackExpoLocation = async () => {
    try {
      const loc = await getLocationQuietly({ timeoutMs: 60000, requestPermission: true });
      if (loc) {
        const lat = loc.coords.latitude;
        const lon = loc.coords.longitude;
        const address = await describeLocation(lat, lon);
        setCurrentLocation({ latitude: lat, longitude: lon, address, isRealGps: true });
        await fetchRiskForCoords(lat, lon);
      } else {
        setCurrentLocation((prev) => ({ ...prev, address: 'Location unavailable – enable GPS / permission' }));
        setRiskData({ category: 'No location', risk_score: 0, factors: {} });
      }
    } catch (e) {
      console.warn('Expo Location error:', e);
      if (locationRef.current.isRealGps) {
        await fetchRiskForCoords(locationRef.current.latitude, locationRef.current.longitude);
      } else {
        setRiskData({ category: 'No location', risk_score: 0, factors: {} });
      }
    } finally {
      setIsRefreshingLocation(false);
    }
  };

  // Fresh, high-accuracy fix used at the moment of an SOS
  const getFreshLocation = async () => {
    const fix = await getLocationQuietly({ timeoutMs: 4000 });
    if (fix) {
      const fresh = {
        ...locationRef.current,
        latitude: fix.coords.latitude,
        longitude: fix.coords.longitude,
        isRealGps: true,
      };
      setCurrentLocation(fresh);
      return fresh;
    }
    return locationRef.current;
  };

  const setCustomLocation = async (lat, lon, label = '') => {
    const newLoc = {
      latitude: parseFloat(lat),
      longitude: parseFloat(lon),
      address: label || `Custom GPS: ${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)}`,
      isRealGps: false,
    };
    setCurrentLocation(newLoc);
    await fetchRiskForCoords(newLoc.latitude, newLoc.longitude);
  };

  const fetchRiskForCoords = async (lat, lon) => {
    try {
      const res = await predictCrimeRisk(lat, lon);
      if (res && res.category) {
        setRiskData(res);
      }
    } catch (e) {
      setRiskData({ category: 'Offline', risk_score: 0, factors: { nearest_hotspot_proximity: 'Server unreachable' } });
    }
  };

  // 3. User Authentication
  const applySession = async (res) => {
    const profile = {
      ...EMPTY_USER,
      ...res.user,
      bloodGroup: res.user.blood_group || res.user.bloodGroup || 'O+',
    };
    setUser(profile);
    setIsLoggedIn(true);
    await saveAuthToken(res.token);
    // The server may have just been changed on the login screen: refresh location-based risk
    detectDeviceLocation();
    await AsyncStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(profile));
    // Server copy wins only if it has guardians; otherwise keep (and upload) the local list
    if (res.user.guardians && res.user.guardians.length > 0) {
      setGuardians(res.user.guardians);
      await AsyncStorage.setItem(STORAGE_KEYS.GUARDIANS, JSON.stringify(res.user.guardians));
    } else if (guardians.length > 0) {
      apiUpdateGuardians(guardians).catch(() => {});
    }
  };

  const loginUser = async (email, password) => {
    try {
      const res = await apiLogin(email.trim(), password);
      if (res && res.success && res.user) {
        await applySession(res);
        return { success: true, user: res.user };
      }
      return { success: false, error: (res && res.error) || 'Login failed' };
    } catch (err) {
      return { success: false, error: 'Cannot reach the SurakshaX server. Check your internet connection and try again.' };
    }
  };

  const registerUser = async (userData) => {
    try {
      const res = await apiRegister(userData);
      if (res && res.success && res.user) {
        await applySession(res);
        return { success: true, user: res.user };
      }
      return { success: false, error: (res && res.error) || 'Registration failed' };
    } catch (err) {
      return { success: false, error: 'Cannot reach the SurakshaX server. Check your internet connection and try again.' };
    }
  };

  const logoutUser = async () => {
    setIsLoggedIn(false);
    setUser(EMPTY_USER);
    await saveAuthToken(null);
    await AsyncStorage.removeItem(STORAGE_KEYS.USER);
  };

  const updateUserProfile = async (newProfile) => {
    const updated = { ...user, ...newProfile };
    setUser(updated);
    await AsyncStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updated));
    // Saved locally first (works offline), then synced to the account
    try {
      await apiUpdateProfile({
        name: updated.name,
        phone: updated.phone,
        gender: updated.gender,
        blood_group: updated.bloodGroup || updated.blood_group,
        date_of_birth: updated.date_of_birth || '',
        address: updated.address || '',
        medical_notes: updated.medical_notes || '',
      });
    } catch (e) {
      console.warn('Profile sync offline, saved locally:', e.message);
    }
  };

  // 4. Guardians: local storage first (works offline), then backend sync
  const updateGuardians = async (newGuardians) => {
    setGuardians(newGuardians);
    await AsyncStorage.setItem(STORAGE_KEYS.GUARDIANS, JSON.stringify(newGuardians));
    try {
      await apiUpdateGuardians(newGuardians);
    } catch (e) {
      console.warn('Backend guardians sync offline, saved locally:', e.message);
    }
  };

  // 5. Incident History
  const logIncident = async ({ trigger, lat, lon, policeStation = 'Unknown', status, trackingUrl }) => {
    const now = new Date();
    const newRecord = {
      id: 'INC-' + Math.floor(100000 + Math.random() * 900000),
      timestamp: Date.now(),
      date_str:
        now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) +
        ' • ' +
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      trigger: trigger || 'Emergency SOS',
      latitude: lat ?? locationRef.current.latitude,
      longitude: lon ?? locationRef.current.longitude,
      police: policeStation,
      status: status || 'Emergency dispatched',
      trackingUrl,
    };

    setIncidents((prev) => {
      const updatedList = [newRecord, ...prev.slice(0, 49)];
      AsyncStorage.setItem(STORAGE_KEYS.INCIDENTS, JSON.stringify(updatedList)).catch(() => {});
      return updatedList;
    });
    return newRecord;
  };

  const clearIncidentHistory = async () => {
    setIncidents([]);
    await AsyncStorage.removeItem(STORAGE_KEYS.INCIDENTS);
  };

  // 6. Emergency Actions & Dispatch
  const startSOSCountdown = (reason = 'Manual SOS Button') => {
    setSosReason(reason);
    setIsSOSActive(true);
  };

  const cancelSOS = () => {
    setIsSOSActive(false);
  };

  // Location updates are pushed by the OS (they keep arriving in the background while the protection
  // service runs), unlike JavaScript timers, which React Native pauses when the app is not on screen.
  const startEmergencyStream = async (sessionId) => {
    stopEmergencyStream();
    const until = Date.now() + 2 * 60 * 60 * 1000; // 2 hours, the server's session validity
    try {
      const sub = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, timeInterval: 5000, distanceInterval: 0 },
        (loc) => {
          if (Date.now() > until) {
            stopEmergencyStream();
            return;
          }
          setCurrentLocation((prev) => ({ ...prev, latitude: loc.coords.latitude, longitude: loc.coords.longitude, isRealGps: true }));
          streamGpsUpdate({
            sessionId,
            userName: user.name,
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
            speed: loc.coords.speed || 0,
            accuracy: loc.coords.accuracy || 0,
          }).catch(() => {});
        }
      );
      emergencyStreamRef.current = sub;
    } catch (e) {
      console.warn('Live location stream unavailable:', e.message);
    }
  };

  /**
   * Emergency sequence:
   *  1. Fresh GPS fix
   *  2. SMS from the phone's own SIM to every guardian (works without internet)
   *  3. Backend dispatch: Twilio SMS/call if configured, nearest police, police dashboard
   *  4. Live location streaming to the tracking link for 2 hours
   */
  const executeDispatch = async (reason, { autoCall = false } = {}) => {
    const trigger = reason || sosReason;
    const loc = await getFreshLocation();
    const sessionId = randomSessionId();
    const trackingUrl = await getLiveTrackingUrl(sessionId);
    // Only a real GPS fix is shared: placeholder or manually chosen test coordinates would mislead
    const hasFix = !!loc.isRealGps;
    const mapsUrl = `https://maps.google.com/?q=${loc.latitude.toFixed(6)},${loc.longitude.toFixed(6)}`;
    const phones = guardians.map((g) => g.phone).filter(Boolean);

    const message =
      `SOS! ${user.name || 'I'} need${user.name ? 's' : ''} help (${trigger}). ` +
      (hasFix
        ? `Location: ${mapsUrl} Live tracking: ${trackingUrl}`
        : `GPS location unavailable - call me now. Live tracking (starts when GPS is found): ${trackingUrl}`) +
      (user.bloodGroup ? ` Blood group: ${user.bloodGroup}.` : '') +
      ' - SurakshaX';

    let smsResults = [];
    try {
      smsResults = await sendEmergencySms(phones, message);
    } catch (e) {
      smsResults = phones.map((phone) => ({ phone, status: 'failed', error: e.message }));
    }

    startEmergencyStream(sessionId);

    // Ring the first contact straight away (no tap needed when Phone permission is granted)
    let callStatus = null;
    if (autoCall && phones[0] && Platform.OS === 'android') {
      callStatus = await placeEmergencyCall(phones[0]).catch(() => 'failed');
    }

    let backend = null;
    let nearestName = hasFix ? 'Unavailable (offline)' : 'GPS unavailable – call 112';
    try {
      if (!hasFix) throw new Error('no GPS fix: police dashboard needs a real location');
      const [policeRes, dispatchRes] = await Promise.all([
        getNearestPoliceStations(loc.latitude, loc.longitude, 1).catch(() => null),
        dispatchEmergencyAlert({
          userName: user.name,
          latitude: loc.latitude,
          longitude: loc.longitude,
          triggerReason: trigger,
          contacts: guardians.map((g) => ({ name: g.name, phone: g.phone, relation: g.relation || 'Guardian' })),
          sessionId,
        }),
      ]);
      // A rejected request (e.g. expired login) comes back as {success:false}: that is not a dispatch
      backend = dispatchRes && dispatchRes.success !== false ? dispatchRes : null;
      const stations = policeRes?.stations || policeRes?.nearest_police_stations || [];
      if (stations.length > 0) {
        // Stations further than 50 km are not a useful answer in an emergency
        nearestName =
          stations[0].distance_km <= 50
            ? `${stations[0].name} (${stations[0].distance_km} km)`
            : 'Outside coverage area – call 112';
      }
    } catch (e) {
      console.warn('Backend dispatch failed:', e.message);
    }

    const smsSent = smsResults.filter((r) => r.status === 'sent').length;
    const composer = smsResults.some((r) => r.status === 'composer_opened');
    const statusParts = [];
    if (phones.length === 0) statusParts.push('No guardians saved');
    else if (smsSent > 0) statusParts.push(`SMS sent to ${smsSent}/${phones.length} guardians`);
    else if (composer) statusParts.push('SMS composer opened');
    else statusParts.push('SMS failed');
    statusParts.push(backend ? 'Police dashboard notified' : 'Server unreachable');

    await logIncident({
      trigger,
      lat: loc.latitude,
      lon: loc.longitude,
      policeStation: nearestName,
      status: statusParts.join(' • '),
      trackingUrl,
    });

    return {
      success: smsSent > 0 || composer || !!backend,
      offline: !backend,
      response: backend,
      nearestPolice: nearestName,
      smsResults,
      callStatus,
      trackingUrl,
      noGuardians: phones.length === 0,
    };
  };

  function stopEmergencyStream() {
    if (emergencyStreamRef.current) {
      emergencyStreamRef.current.remove?.();
      emergencyStreamRef.current = null;
    }
  }

  return (
    <SafetyContext.Provider
      value={{
        isAuthLoaded,
        isLoggedIn,
        user,
        guardians,
        currentLocation,
        riskData,
        incidents,
        isRefreshingLocation,
        isSOSActive,
        sosReason,
        loginUser,
        registerUser,
        logoutUser,
        updateUserProfile,
        updateGuardians,
        logIncident,
        clearIncidentHistory,
        startSOSCountdown,
        cancelSOS,
        executeDispatch,
        stopEmergencyStream,
        detectDeviceLocation,
        setCustomLocation,
        fetchRiskForCoords,
      }}
    >
      {children}
    </SafetyContext.Provider>
  );
};

export const useSafety = () => useContext(SafetyContext);
