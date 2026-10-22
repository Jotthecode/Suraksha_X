# SurakshaX Mobile (Expo React Native Android App)

SurakshaX is an autonomous AI-based personal safety platform for Android. This application has been converted from native Java into an **Expo React Native** app featuring a modern **Samsung One UI design system**, preserving **100% of the safety features** and connecting directly to the Python AI backend (`backend/app.py`).

---

## 🌟 Key Features & Architecture Parity

| # | Feature | Details & Backend Link |
|---|---|---|
| 1 | **Samsung One UI Dashboard** | Header viewing area + bottom-weighted interaction area, real-time Random Forest crime risk badge (`POST /predict_risk`), and sensor telemetry simulation (`POST /analyze_status`). |
| 2 | **Pulsing SOS Emergency Button** | Tactile pulsing ripple animation with haptic feedback triggering fail-safe 10-second countdown. |
| 3 | **Automated Emergency Dispatch** | Multi-channel dispatch via Twilio SMS and automated voice calls (`POST /emergency_dispatch`), plus direct carrier dialer fallback. |
| 4 | **Modified Dijkstra Safe Routing** | Interactive OpenStreetMap / Leaflet map avoiding crime hotspots (`POST /safe_route`, `GET /hotspots`), with safety-distance alpha slider ($\alpha = 0.40$). |
| 5 | **Live GPS Tracking Beacon** | 5-second streaming updates to the backend (`POST /tracking/update`), generating a secure live tracking web link for guardians (`/track/<sessionId>`). |
| 6 | **Nearest Police Radar** | Haversine distance calculator identifying closest stations with one-touch direct dial and 112 emergency calling (`POST /police/nearest`). |
| 7 | **Distress Voice Recognition** | CNN voice distress detector recognizing keywords like `"Bachao"` (`POST /voice_sos`). |
| 8 | **Guardians & Contacts Manager** | Persistent storage (`AsyncStorage`) for primary and secondary emergency guardians with quick-call buttons. |
| 9 | **Incident History & Audit Log** | Local timestamped audit log of all triggered alerts, coordinates, and response statuses. |
| 10 | **Backend Configuration** | Configurable backend endpoint (presets for Android Emulator `10.0.2.2:5000`, Web `localhost:5000`, or Render Cloud `backend-suraksha-x.onrender.com`). |

---

## 🚀 How to Run the App

### 1. Start the Python AI Backend Server
In your root terminal:
```powershell
python backend/app.py
```
*(The Flask backend will start on `http://127.0.0.1:5000`)*

### 2. Launch the Mobile App
Open a terminal in the `mobile` directory:
```powershell
cd mobile
npm start
```

### 3. Open on Web & Mobile Concurrently
- **Run on Web directly**:
  ```powershell
  npm run web
  ```
  *(Launches the Expo React Native app in your default browser at `http://localhost:8081`)*
- **Run on Android Emulator**: Press `a` in the Expo terminal (or run `npm run android`).
- **Physical Phone (Expo Go)**: Scan the QR code displayed in the terminal with the Expo Go app.
- **Flask Built-in Web App**:
  You can also open `http://localhost:5000/web` in any browser to access the Python Flask embedded web simulator.

---

## 📁 Project Structure

```
mobile/
├── App.js                    # Root entry point with Providers
├── app.json                  # Expo config & Android permissions
├── package.json              # Dependencies
└── src/
    ├── api/
    │   └── config.js         # API client & backend endpoints
    ├── components/
    │   ├── OneUICard.js      # Samsung One UI rounded card
    │   ├── OneUIHeader.js    # One UI large header & status badge
    │   ├── PulsingSOSButton.js # Animated SOS panic trigger
    │   └── LeafletMapView.js # Cross-platform map & hotspots overlay
    ├── context/
    │   └── SafetyContext.js  # Global state (location, risk, telemetry, guardians)
    ├── navigation/
    │   └── AppNavigator.js   # Bottom tabs (Home, Route, Beacon, Contacts, Profile) + Modal stack
    ├── screens/
    │   ├── DashboardScreen.js
    │   ├── AlertsScreen.js
    │   ├── SafeRouteScreen.js
    │   ├── LiveTrackingScreen.js
    │   ├── ContactsScreen.js
    │   ├── PoliceStationsScreen.js
    │   ├── SafetyHistoryScreen.js
    │   ├── ProfileScreen.js
    │   ├── LoginScreen.js
    │   └── RegisterScreen.js
    └── theme/
        └── colors.js         # One UI color tokens, typography & radii
```
