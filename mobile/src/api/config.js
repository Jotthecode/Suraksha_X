import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

export const PREF_SERVER_URL = 'surakshax_server_base_url';
export const PREF_AUTH_TOKEN = 'surakshax_auth_token';

// Local dev host: Android emulator uses 10.0.2.2 to reach the host PC, iOS simulator/web uses localhost
export const DEFAULT_DEV_HOST = Platform.OS === 'android' ? 'http://10.0.2.2:5000' : 'http://localhost:5000';
// Production backend (server/ deployed with render.yaml). Override at build time with EXPO_PUBLIC_API_URL.
export const CLOUD_HOST = (process.env.EXPO_PUBLIC_API_URL || 'https://surakshax-api.onrender.com').replace(/\/+$/, '');
// Release builds (the APK) talk to the cloud backend by default; dev builds use the local server.
// The production web build is served by the backend itself (/app), so it talks to its own origin.
const WEB_ORIGIN = Platform.OS === 'web' && typeof window !== 'undefined' ? window.location.origin : null;
export const DEFAULT_HOST = __DEV__ ? DEFAULT_DEV_HOST : WEB_ORIGIN || CLOUD_HOST;

// Render free instances sleep when idle and take ~30-50 s to wake up.
const REQUEST_TIMEOUT_MS = 45000;

export const getBaseUrl = async () => {
  try {
    const saved = await AsyncStorage.getItem(PREF_SERVER_URL);
    if (saved && saved.trim().length > 0) {
      return saved.trim().replace(/\/+$/, '');
    }
  } catch (e) {
    console.warn('Error reading base URL:', e);
  }
  return DEFAULT_HOST;
};

export const setBaseUrl = async (url) => {
  try {
    await AsyncStorage.setItem(PREF_SERVER_URL, url.trim());
  } catch (e) {
    console.error('Error saving base URL:', e);
  }
};

const getAuthToken = async () => {
  try {
    return (await AsyncStorage.getItem(PREF_AUTH_TOKEN)) || '';
  } catch (e) {
    return '';
  }
};

export const saveAuthToken = async (token) => {
  try {
    if (token) await AsyncStorage.setItem(PREF_AUTH_TOKEN, token);
    else await AsyncStorage.removeItem(PREF_AUTH_TOKEN);
  } catch (e) {}
};

const buildHeaders = async (isJson = true) => {
  const headers = { Accept: 'application/json' };
  if (isJson) headers['Content-Type'] = 'application/json';
  const token = await getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
};

const fetchJson = async (url, method, body, timeoutMs) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const options = { method, headers: await buildHeaders(), signal: controller.signal };
    if (body) options.body = JSON.stringify(body);
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      // Auth endpoints answer {success:false,error} with 4xx: surface that message instead of a network error
      if (payload && payload.error) return { ...payload, success: false, status: response.status };
      throw new Error(`HTTP Error ${response.status}`);
    }
    return payload;
  } finally {
    clearTimeout(timeoutId);
  }
};

/**
 * Fetch wrapper with timeout & cloud fallback
 */
const apiRequest = async (endpoint, method = 'GET', body = null, { timeoutMs = REQUEST_TIMEOUT_MS } = {}) => {
  const baseUrl = await getBaseUrl();
  try {
    return await fetchJson(`${baseUrl}${endpoint}`, method, body, timeoutMs);
  } catch (primaryErr) {
    console.warn(`Request failed to ${baseUrl}${endpoint}:`, primaryErr.message);
    // If a custom URL failed and it is not the cloud host, try the cloud host
    if (baseUrl !== CLOUD_HOST) {
      try {
        return await fetchJson(`${CLOUD_HOST}${endpoint}`, method, body, timeoutMs);
      } catch (fallbackErr) {
        console.warn('Cloud fallback also failed:', fallbackErr.message);
      }
    }
    throw primaryErr;
  }
};

// Wake a sleeping free-tier backend early (fire-and-forget)
export const warmUpBackend = async () => {
  try {
    await apiRequest('/health', 'GET', null, { timeoutMs: 60000 });
    return true;
  } catch (e) {
    return false;
  }
};

// 1. Predict Crime Hotspot Risk
export const predictCrimeRisk = async (latitude, longitude) => {
  // Lighting / activity / police distance are derived server-side from OpenStreetMap
  return await apiRequest('/predict_risk', 'POST', {
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
  });
};

// 2. Multi-Modal Sensor Telemetry (HDT)
export const analyzeSensorStatus = async ({ audioScore = 0.1, fallForce = 1.0, heartRate = 72, latitude = 18.4550, longitude = 73.9050 }) => {
  return await apiRequest('/analyze_status', 'POST', {
    audio_score: parseFloat(audioScore),
    fall_force: parseFloat(fallForce),
    heart_rate: parseFloat(heartRate),
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
  });
};

// 3. Safe Route Recommendation (OSRM road alternatives scored by crime risk)
const normalizeRoute = (route) =>
  route && {
    path_coords: (route.waypoints || []).map((w) => [w.lat, w.lon]),
    distance_km: route.total_distance_km,
    average_risk_score: route.mean_risk_score,
    high_risk_segments: route.high_risk_segments,
    steps: route.steps || [],
  };

export const calculateSafeRoute = async ({ originLat, originLon, destLat, destLon, alpha = 0.4 }) => {
  const res = await apiRequest('/safe_route', 'POST', {
    origin: { latitude: parseFloat(originLat), longitude: parseFloat(originLon) },
    destination: { latitude: parseFloat(destLat), longitude: parseFloat(destLon) },
    alpha: parseFloat(alpha),
  });
  if (!res || res.error) throw new Error(res?.error || 'Route planning failed');
  const m = res.metrics_comparison || {};
  const sign = m.distance_increase_percent >= 0 ? '+' : '';
  return {
    ...res,
    safest_route: normalizeRoute(res.safe_route),
    shortest_route: normalizeRoute(res.shortest_route),
    tradeoff_summary: !String(res.data_source || '').startsWith('openstreetmap')
      ? `${res.candidates_evaluated} ${res.travel_mode} routes found, but map data for risk scoring is unavailable right now, so the shortest route is shown. Try again in a minute.`
      : m.distance_increase_percent === 0
      ? `Compared ${res.candidates_evaluated} ${res.travel_mode} routes: the shortest route is also the safest.`
      : `Compared ${res.candidates_evaluated} ${res.travel_mode} routes: ${sign}${m.distance_increase_percent}% distance for ${m.risk_reduction_percent}% lower crime risk.`,
  };
};

// 3b. Address search inside India (OpenStreetMap Nominatim via the backend)
export const geocodeAddress = async (query, near) => {
  const bias = near ? `&lat=${near.lat}&lon=${near.lon}` : '';
  const res = await apiRequest(`/geocode?q=${encodeURIComponent(query)}${bias}`, 'GET', null, { timeoutMs: 20000 });
  return (res && res.results) || [];
};

// 3c. Type-ahead place suggestions (free OpenStreetMap search via the backend, nearest first)
export const suggestPlaces = async (query, near, { limit = 8 } = {}) => {
  const bias = near ? `&lat=${near.lat}&lon=${near.lon}` : '';
  const res = await apiRequest(`/places/suggest?q=${encodeURIComponent(query)}${bias}&limit=${limit}`, 'GET', null, {
    timeoutMs: 12000,
  });
  return (res && res.results) || [];
};

// 3d. Short address label for a coordinate
export const reverseGeocode = async (latitude, longitude) => {
  const res = await apiRequest(`/places/reverse?lat=${latitude}&lon=${longitude}`, 'GET', null, { timeoutMs: 12000 });
  return (res && res.label) || null;
};

// 4. Retrieve Crime Hotspots for Map Overlay
export const getCrimeHotspots = async (latitude, longitude) => {
  return await apiRequest(`/hotspots?lat=${parseFloat(latitude)}&lon=${parseFloat(longitude)}`, 'GET');
};

// 5. CNN Voice Distress Keyword Recognizer (text transcript fallback)
export const testVoiceSosKeyword = async (phrase = 'Bachao', audioScore = 0.88) => {
  return await apiRequest('/voice_sos', 'POST', {
    phrase,
    audio_score: parseFloat(audioScore),
    noise_condition: 'street',
  });
};

// 5b. Real recorded audio clip -> trained CNN on the backend
export const classifyVoiceAudio = async (fileUri, { timeoutMs = 20000 } = {}) => {
  const baseUrl = await getBaseUrl();
  const ext = (fileUri.split('.').pop() || 'm4a').toLowerCase();
  const form = new FormData();
  form.append('audio', { uri: fileUri, name: `clip.${ext}`, type: ext === 'wav' ? 'audio/wav' : 'audio/mp4' });

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl}/voice_sos`, {
      method: 'POST',
      headers: await buildHeaders(false),
      body: form,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timeoutId);
  }
};

// 6. Nearest Police Stations (Haversine distance)
export const getNearestPoliceStations = async (latitude, longitude, count = 5) => {
  return await apiRequest('/police/nearest', 'POST', {
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    count: parseInt(count, 10),
  });
};

// 7. Automated Emergency Dispatch (Twilio SMS/Call + Police dashboard)
export const dispatchEmergencyAlert = async ({ userName, latitude, longitude, triggerReason, contacts, sessionId }) => {
  return await apiRequest('/emergency_dispatch', 'POST', {
    session_id: sessionId,
    user_name: userName,
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    trigger_reason: triggerReason,
    contacts: contacts || [],
  });
};

// 8. Live GPS Tracking Beacon Update
export const streamGpsUpdate = async ({ sessionId, latitude, longitude, speed = 0.0, accuracy = 5.0, battery = 85, userName }) => {
  return await apiRequest('/tracking/update', 'POST', {
    session_id: sessionId,
    user_name: userName,
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    speed: parseFloat(speed),
    accuracy: parseFloat(accuracy),
    battery: `${parseInt(battery, 10)}%`,
  });
};

// 9. Get Live Tracking Web URL
export const getLiveTrackingUrl = async (sessionId) => {
  const base = await getBaseUrl();
  return `${base}/track/${sessionId}`;
};

// 10. Backend User Authentication & Sync
export const apiLogin = async (email, password) => {
  return await apiRequest('/api/login', 'POST', { email, password });
};

export const apiRegister = async (userData) => {
  return await apiRequest('/api/register', 'POST', userData);
};

export const apiGetProfile = async () => {
  return await apiRequest('/api/user/profile', 'GET');
};

export const apiUpdateProfile = async (profile) => {
  return await apiRequest('/api/user/profile', 'PUT', profile);
};

export const apiUpdateGuardians = async (guardians) => {
  return await apiRequest('/api/user/guardians', 'POST', { guardians });
};
