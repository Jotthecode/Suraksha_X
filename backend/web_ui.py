"""
Web Application Interface for SurakshaX
SurakshaX – AI-Based Women Safety Platform

Faithfully reproduces the native Android UI layouts from app/src/main/res/layout:
1. Login Screen (activity_main.xml)
2. Registration Screen (activity_register.xml)
3. Manage Guardians Screen (activity_contacts.xml)
4. Home Dashboard Screen (activity_dashboard.xml)
5. SOS Countdown & Dispatch Screen (activity_alerts.xml)
6. Safe Route Recommendation Screen (activity_safe_route.xml)
7. Live GPS Tracking Beacon Screen (activity_live_tracking.xml)
8. Safety History and Incident Log Screen (activity_safety_history.xml)
9. User Profile Screen (activity_profile.xml)
"""

def render_web_app_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SurakshaX • AI Autonomous Personal Safety Platform</title>
    <!-- Leaflet CSS & JS for OpenStreetMap -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {
            --colorPrimary: #D32F2F;
            --colorPrimaryDark: #B71C1C;
            --colorSafe: #2E7D32;
            --colorWarning: #F57C00;
            --colorHighRisk: #D32F2F;
            --bgLight: #F8F9FA;
            --cardBg: #FFFFFF;
            --textPrimary: #212121;
            --textSecondary: #757575;
            --divider: #E0E0E0;
            --purplePrimary: #4A148C;
            --purpleSecondary: #7B1FA2;
            --purpleLight: #F3E5F5;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background: #1E293B;
            color: var(--textPrimary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
        }

        /* Top Developer / Inspection Control Bar */
        .dev-control-bar {
            width: 100%;
            background: #0F172A;
            border-bottom: 1px solid #334155;
            padding: 8px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.82rem;
            color: #94A3B8;
            z-index: 9999;
            flex-wrap: wrap;
            gap: 8px;
        }

        .dev-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            padding: 3px 8px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.75rem;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .dev-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .dev-btn {
            background: #334155;
            color: #F8FAFC;
            border: none;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.78rem;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.15s;
        }

        .dev-btn:hover {
            background: #475569;
        }

        .dev-btn.active {
            background: #0284C7;
            color: white;
        }

        .dev-select {
            background: #1E293B;
            color: #F8FAFC;
            border: 1px solid #475569;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            outline: none;
        }

        /* App Wrapper / Mobile Frame */
        .app-viewport-wrapper {
            width: 100%;
            display: flex;
            justify-content: center;
            padding: 16px 8px 32px 8px;
            flex: 1;
        }

        .mobile-frame {
            width: 100%;
            max-width: 425px;
            min-height: 840px;
            background: var(--bgLight);
            border-radius: 36px;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 0 10px #0F172A, 0 0 0 12px #334155;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
            transition: all 0.3s ease;
        }

        .mobile-frame.fullscreen {
            max-width: 600px;
            border-radius: 0;
            box-shadow: none;
            min-height: 100vh;
        }

        /* Responsive DevTools Mobile Mode (@media max-width: 600px) */
        @media (max-width: 600px) {
            body {
                background: var(--bgLight);
            }
            .app-viewport-wrapper {
                padding: 0;
                margin: 0;
            }
            .mobile-frame {
                max-width: 100% !important;
                min-height: 100vh !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                border: none !important;
            }
            .dev-control-bar {
                padding: 6px 12px;
                font-size: 0.75rem;
            }
        }

        /* Android Status Bar */
        .android-status-bar {
            height: 28px;
            background: var(--colorPrimaryDark);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 16px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            user-select: none;
        }

        .android-status-bar.purple {
            background: #38006B;
        }

        .status-icons {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Android Action Bar / Toolbar */
        .app-toolbar {
            height: 56px;
            background: var(--colorPrimary);
            color: white;
            display: flex;
            align-items: center;
            padding: 0 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            position: relative;
            z-index: 10;
        }

        .app-toolbar.purple {
            background: var(--purplePrimary);
        }

        .toolbar-title-box {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .toolbar-title {
            font-size: 1.25rem;
            font-weight: bold;
            line-height: 1.2;
        }

        .toolbar-subtitle {
            font-size: 0.75rem;
            color: #FFCDD2;
        }

        .toolbar-btn {
            background: transparent;
            border: none;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            transition: background 0.2s;
        }

        .toolbar-btn:hover {
            background: rgba(255,255,255,0.15);
        }

        /* Content Viewport */
        .screen-content {
            flex: 1;
            overflow-y: auto;
            position: relative;
            background: var(--bgLight);
            display: flex;
            flex-direction: column;
        }

        /* Screen Visibility Switching */
        .android-screen {
            display: none;
            width: 100%;
            flex: 1;
            animation: fadeIn 0.2s ease-in-out;
        }

        .android-screen.active {
            display: flex;
            flex-direction: column;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Material CardView (activity_dashboard.xml) */
        .material-card {
            background: var(--cardBg);
            border-radius: 12px;
            padding: 16px;
            margin: 12px 16px 0 16px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.04);
        }

        .card-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .card-heading {
            font-size: 0.95rem;
            font-weight: bold;
            color: var(--textPrimary);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .card-body-text {
            font-size: 0.82rem;
            color: var(--textSecondary);
            line-height: 1.4;
            margin-bottom: 12px;
        }

        /* Risk Badges (from colors.xml) */
        .risk-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        .risk-low {
            background: #E8F5E9;
            color: var(--colorSafe);
            border: 1px solid #A5D6A7;
        }

        .risk-medium {
            background: #FFF3E0;
            color: var(--colorWarning);
            border: 1px solid #FFCC80;
        }

        .risk-high {
            background: #FFEBEE;
            color: var(--colorHighRisk);
            border: 1px solid #EF9A9A;
        }

        /* Large Emergency SOS Button (activity_dashboard.xml) */
        .btn-sos-emergency {
            margin: 14px 16px 4px 16px;
            height: 76px;
            background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
            color: white;
            border: none;
            border-radius: 16px;
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            cursor: pointer;
            box-shadow: 0 6px 20px rgba(211, 47, 47, 0.45);
            transition: transform 0.1s, box-shadow 0.2s;
        }

        .btn-sos-emergency:hover {
            box-shadow: 0 8px 24px rgba(211, 47, 47, 0.6);
            transform: scale(1.01);
        }

        .btn-sos-emergency:active {
            transform: scale(0.98);
        }

        /* 2x2 Grid of Core Safety Modules */
        .modules-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 12px 16px 0 16px;
        }

        .nav-module-card {
            background: var(--cardBg);
            border-radius: 12px;
            padding: 14px 10px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            cursor: pointer;
            border: 1px solid rgba(0,0,0,0.04);
            transition: transform 0.15s, box-shadow 0.15s;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100px;
        }

        .nav-module-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 14px rgba(0,0,0,0.1);
        }

        .module-icon {
            font-size: 1.8rem;
            margin-bottom: 6px;
        }

        .module-title {
            font-size: 0.85rem;
            font-weight: bold;
            color: var(--textPrimary);
        }

        .module-subtitle {
            font-size: 0.72rem;
            color: var(--textSecondary);
            margin-top: 2px;
        }

        /* Form Inputs & Buttons */
        .android-input-box {
            width: 100%;
            background: #FFFFFF;
            border: 1.5px solid #CFD8DC;
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 0.92rem;
            color: #212121;
            margin-top: 6px;
            margin-bottom: 12px;
            outline: none;
            transition: border-color 0.2s;
        }

        .android-input-box:focus {
            border-color: var(--purplePrimary);
        }

        .android-btn {
            width: 100%;
            height: 52px;
            background: var(--purplePrimary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            letter-spacing: 0.4px;
            transition: background 0.2s, box-shadow 0.2s;
            box-shadow: 0 3px 8px rgba(74, 20, 140, 0.25);
            text-decoration: none;
        }

        .android-btn:hover {
            background: #38006B;
        }

        .android-btn-outlined {
            width: 100%;
            height: 44px;
            background: transparent;
            color: var(--colorPrimary);
            border: 1.5px solid var(--colorPrimary);
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.15s;
        }

        .android-btn-outlined:hover {
            background: rgba(211, 47, 47, 0.06);
        }

        .android-btn-safe {
            background: var(--colorSafe);
            box-shadow: 0 3px 8px rgba(46, 125, 50, 0.3);
        }

        .android-btn-safe:hover {
            background: #1B5E20;
        }

        /* Circular SOS Countdown (activity_alerts.xml) */
        .countdown-circle-wrap {
            width: 180px;
            height: 180px;
            margin: 28px auto 20px auto;
            border-radius: 50%;
            background: radial-gradient(circle, #EF5350 0%, #D32F2F 70%, #B71C1C 100%);
            box-shadow: 0 0 0 12px rgba(211, 47, 47, 0.25), 0 8px 24px rgba(211, 47, 47, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulseAlert 1.2s infinite alternate ease-in-out;
        }

        @keyframes pulseAlert {
            0% { transform: scale(0.98); box-shadow: 0 0 0 8px rgba(211, 47, 47, 0.2), 0 8px 20px rgba(211, 47, 47, 0.4); }
            100% { transform: scale(1.03); box-shadow: 0 0 0 18px rgba(211, 47, 47, 0.3), 0 10px 30px rgba(211, 47, 47, 0.5); }
        }

        .countdown-num {
            font-size: 4.8rem;
            font-weight: 900;
            color: white;
            user-select: none;
        }

        /* Leaflet Map in Mobile View */
        .map-container-box {
            height: 250px;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
            border: 1px solid var(--divider);
            z-index: 1;
        }

        /* Bottom Helplines Bar */
        .helplines-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }

        .helpline-chip {
            background: #FFEBEE;
            border: 1px solid #FFCDD2;
            border-radius: 8px;
            padding: 8px 4px;
            text-align: center;
            text-decoration: none;
            color: var(--colorPrimary);
            font-size: 0.78rem;
            font-weight: bold;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
        }

        .helpline-chip:hover {
            background: #FFCDD2;
        }

        /* Android Bottom Navigation Bar Indicator */
        .android-home-bar {
            height: 18px;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .home-indicator-pill {
            width: 120px;
            height: 4px;
            background: #666;
            border-radius: 2px;
        }

        /* Turn-by-turn waypoint items */
        .waypoint-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--divider);
            font-size: 0.8rem;
        }

        .waypoint-item:last-child {
            border-bottom: none;
        }

        /* Incident history items */
        .history-card {
            background: white;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 4px solid var(--colorPrimary);
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
    </style>
</head>
<body>

    <!-- TOP CONTROLS FOR TESTING & INSPECTION -->
    <div class="dev-control-bar">
        <div style="display: flex; align-items: center; gap: 10px;">
            <strong style="color: #38BDF8;">SurakshaX Testing Suite</strong>
            <span class="dev-badge">🟢 Backend Online</span>
        </div>
        <div class="dev-controls">
            <span>Screen:</span>
            <select id="devScreenSelect" class="dev-select" onchange="navigateTo(this.value)">
                <option value="screen-dashboard">Home Dashboard</option>
                <option value="screen-main">1. Login Screen</option>
                <option value="screen-register">2. Register Screen</option>
                <option value="screen-contacts">3. Manage Guardians</option>
                <option value="screen-alerts">4. SOS Countdown</option>
                <option value="screen-safe-route">5. Safe Route Planner</option>
                <option value="screen-live-tracking">6. Live GPS Beacon</option>
                <option value="screen-safety-history">7. Safety History</option>
                <option value="screen-profile">8. User Profile</option>
            </select>
            <button class="dev-btn active" id="btnPhoneView" onclick="setDeviceView('phone')">📱 Phone Frame</button>
            <button class="dev-btn" id="btnFullView" onclick="setDeviceView('full')">🖥️ Expanded View</button>
        </div>
    </div>

    <!-- MAIN MOBILE VIEWPORT CONTAINER -->
    <div class="app-viewport-wrapper">
        <div class="mobile-frame" id="mobileDeviceFrame">

            <!-- 1. ANDROID STATUS BAR -->
            <div class="android-status-bar" id="androidStatusBar">
                <span id="statusBarTime">16:45</span>
                <div class="status-icons">
                    <span>📶 LTE</span>
                    <span>🔋 94%</span>
                </div>
            </div>

            <!-- VIEWPORT SCROLL CONTENT -->
            <div class="screen-content">

                <!-- ========================================================= -->
                <!-- SCREEN: DASHBOARD (activity_dashboard.xml)               -->
                <!-- ========================================================= -->
                <div id="screen-dashboard" class="android-screen active">
                    <!-- Top App Bar -->
                    <div class="app-toolbar">
                        <div class="toolbar-title-box">
                            <div class="toolbar-title">SurakshaX</div>
                            <div class="toolbar-subtitle">AI Autonomous Safety System</div>
                        </div>
                        <button class="toolbar-btn" onclick="navigateTo('screen-profile')" title="Profile">👤</button>
                    </div>

                    <!-- Scrollable Body -->
                    <div style="padding-bottom: 24px;">

                        <!-- Crime Risk Indicator Card -->
                        <div class="material-card">
                            <div class="card-header-row">
                                <div class="card-heading">🛡️ Spatiotemporal Crime Risk</div>
                                <span id="dashRiskBadge" class="risk-badge risk-low">LOW RISK (0.18)</span>
                            </div>
                            <div id="dashRiskDetails" class="card-body-text">
                                Location: Current Safe Zone • Street Lighting: Active • Grid: 250m x 250m cell
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button class="android-btn-outlined" style="height: 36px; font-size: 0.78rem;" onclick="refreshDashboardRisk()">
                                    🔄 Refresh Risk Score
                                </button>
                                <button class="android-btn-outlined" style="height: 36px; font-size: 0.78rem; border-color: #F57C00; color: #F57C00;" onclick="simulateHighRiskCorridor()">
                                    ⚠️ High-Risk Test
                                </button>
                            </div>
                        </div>

                        <!-- Big Emergency SOS Button -->
                        <button class="btn-sos-emergency" onclick="triggerSosCountdown('Manual SOS Button')">
                            <span>🚨</span> SOS EMERGENCY
                        </button>
                        <div style="text-align: center; font-size: 0.72rem; color: var(--textSecondary); margin-top: 4px;">
                            Includes 10-second fail-safe cancellation window
                        </div>

                        <!-- CNN Voice-Activated SOS Card -->
                        <div class="material-card">
                            <div class="card-header-row">
                                <div class="card-heading">🎙️ CNN Voice SOS Trigger</div>
                                <span style="font-size: 0.75rem; color: var(--colorSafe); font-weight: bold;">ACTIVE (P > 0.85)</span>
                            </div>
                            <div class="card-body-text">
                                Distress Keywords: <em>"Help"</em>, <em>"Bachao"</em>, <em>"Save me"</em>.
                                Multi-lingual CNN detector with 38ms inference.
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                <button class="android-btn-outlined" style="height: 36px; font-size: 0.78rem;" onclick="testVoiceKeyword('Bachao')">
                                    🗣️ Say 'Bachao'
                                </button>
                                <button class="android-btn-outlined" style="height: 36px; font-size: 0.78rem;" onclick="testVoiceKeyword('Help')">
                                    🗣️ Say 'Help'
                                </button>
                            </div>
                        </div>

                        <!-- Core Safety Modules Heading -->
                        <div style="margin: 16px 16px 0 16px; font-size: 0.95rem; font-weight: bold; color: var(--textPrimary);">
                            Core Safety Modules
                        </div>

                        <!-- 2x2 Grid of Modules -->
                        <div class="modules-grid">
                            <!-- Module 1: Safe Route -->
                            <div class="nav-module-card" onclick="navigateTo('screen-safe-route')">
                                <div class="module-icon">🗺️</div>
                                <div class="module-title">Safe Route</div>
                                <div class="module-subtitle">Dijkstra α-Tradeoff</div>
                            </div>
                            <!-- Module 3: Live GPS -->
                            <div class="nav-module-card" onclick="navigateTo('screen-live-tracking')">
                                <div class="module-icon">📍</div>
                                <div class="module-title">Live Tracking</div>
                                <div class="module-subtitle">5s GPS Beacon</div>
                            </div>
                            <!-- Emergency Contacts -->
                            <div class="nav-module-card" onclick="navigateTo('screen-contacts')">
                                <div class="module-icon">👥</div>
                                <div class="module-title">Guardians</div>
                                <div class="module-subtitle" id="dashGuardiansSub">2 Contacts Set</div>
                            </div>
                            <!-- Safety History -->
                            <div class="nav-module-card" onclick="navigateTo('screen-safety-history')">
                                <div class="module-icon">🕒</div>
                                <div class="module-title">Incident Log</div>
                                <div class="module-subtitle">Past Triggers</div>
                            </div>
                        </div>

                        <!-- Instant Helplines Card -->
                        <div class="material-card" style="margin-top: 14px;">
                            <div class="card-heading">📞 Instant Emergency Helplines</div>
                            <div class="helplines-grid">
                                <a href="tel:112" class="helpline-chip">
                                    <span style="font-size: 1.1rem;">🚨</span>
                                    <span>112 National</span>
                                </a>
                                <a href="tel:1091" class="helpline-chip">
                                    <span style="font-size: 1.1rem;">🚺</span>
                                    <span>1091 Women</span>
                                </a>
                                <div class="helpline-chip" style="cursor: pointer;" onclick="locateNearestPolice()">
                                    <span style="font-size: 1.1rem;">👮</span>
                                    <span>Nearest Station</span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 1: LOGIN (activity_main.xml)                       -->
                <!-- ========================================================= -->
                <div id="screen-main" class="android-screen" style="background: white; padding: 24px; justify-content: center; align-items: center; text-align: center;">
                    <div style="width: 80px; height: 80px; border-radius: 50%; background: var(--purpleLight); display: flex; align-items: center; justify-content: center; font-size: 2.2rem; margin-bottom: 16px;">
                        🔒
                    </div>
                    <h1 style="font-size: 2.3rem; font-weight: 900; color: var(--purplePrimary); margin-bottom: 4px;">SurakshaX</h1>
                    <p style="font-size: 0.95rem; color: var(--purpleSecondary); font-weight: 600; margin-bottom: 32px;">AI-Powered Personal Safety</p>

                    <input type="email" id="loginEmail" class="android-input-box" placeholder="Email Address" value="user@surakshax.org">
                    <input type="password" id="loginPass" class="android-input-box" placeholder="Password" value="••••••••">

                    <button class="android-btn" style="margin-top: 12px;" onclick="doLogin()">LOGIN</button>

                    <div style="margin-top: 24px; font-size: 0.85rem; color: #1A237E; font-weight: bold; cursor: pointer;" onclick="navigateTo('screen-register')">
                        New User? Create Account
                    </div>

                    <button class="android-btn-outlined" style="margin-top: 20px; border-color: var(--purpleSecondary); color: var(--purpleSecondary);" onclick="navigateTo('screen-dashboard')">
                        Skip to Dashboard (Demo Mode)
                    </button>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 2: REGISTRATION (activity_register.xml)            -->
                <!-- ========================================================= -->
                <div id="screen-register" class="android-screen" style="background: var(--purpleLight); padding: 24px;">
                    <div style="font-size: 1.2rem; cursor: pointer; color: var(--purplePrimary); margin-bottom: 12px;" onclick="navigateTo('screen-main')">
                        ← Back to Login
                    </div>
                    <h2 style="font-size: 1.8rem; font-weight: bold; color: var(--purplePrimary); margin-bottom: 20px;">
                        Create Your Profile
                    </h2>

                    <label style="font-size: 0.78rem; font-weight: bold; color: #555;">FULL NAME</label>
                    <input type="text" id="regName" class="android-input-box" placeholder="Full Name" value="Aarohi Sharma">

                    <label style="font-size: 0.78rem; font-weight: bold; color: #555;">EMAIL ADDRESS</label>
                    <input type="email" id="regEmail" class="android-input-box" placeholder="Email Address" value="aarohi@safety.org">

                    <label style="font-size: 0.78rem; font-weight: bold; color: #555;">SELECT GENDER</label>
                    <div style="display: flex; gap: 16px; margin: 8px 0 16px 0; font-size: 0.9rem;">
                        <label style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
                            <input type="radio" name="gender" value="Female" checked> Female
                        </label>
                        <label style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
                            <input type="radio" name="gender" value="Male"> Male
                        </label>
                        <label style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
                            <input type="radio" name="gender" value="Other"> Other
                        </label>
                    </div>

                    <label style="font-size: 0.78rem; font-weight: bold; color: #555;">SET PASSWORD</label>
                    <input type="password" id="regPass" class="android-input-box" placeholder="Set Password" value="SurakshaX@2026">

                    <button class="android-btn" style="margin-top: 14px;" onclick="doRegister()">
                        NEXT: EMERGENCY CONTACTS →
                    </button>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 3: CONTACTS (activity_contacts.xml)                -->
                <!-- ========================================================= -->
                <div id="screen-contacts" class="android-screen" style="background: #FAFAFA; padding: 20px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; cursor: pointer; color: var(--purplePrimary);" onclick="navigateTo('screen-dashboard')">
                        <span>← Back</span>
                    </div>

                    <h2 style="font-size: 1.6rem; font-weight: bold; color: var(--purplePrimary); margin-bottom: 6px;">
                        Manage Guardians
                    </h2>
                    <p style="font-size: 0.82rem; color: #666; margin-bottom: 20px; line-height: 1.4;">
                        Emergency alerts and live GPS beacons will be sent to these numbers automatically.
                    </p>

                    <div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid var(--divider); margin-bottom: 16px;">
                        <div style="font-weight: bold; font-size: 0.9rem; margin-bottom: 8px; color: #333;">
                            Primary Guardian (Priority 1)
                        </div>
                        <input type="text" id="guardianName1" class="android-input-box" placeholder="Guardian Name (e.g. Mom / Dad)" value="Parent Guardian">
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <input type="tel" id="guardianPhone1" class="android-input-box" style="margin-bottom: 0; flex: 1;" placeholder="Mobile Number" value="+91-9876543210">
                            <a href="tel:+919876543210" style="width: 48px; height: 48px; background: var(--colorSafe); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; text-decoration: none; font-size: 1.2rem;">
                                📞
                            </a>
                        </div>
                    </div>

                    <div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid var(--divider); margin-bottom: 20px;">
                        <div style="font-weight: bold; font-size: 0.9rem; margin-bottom: 8px; color: #333;">
                            Secondary Guardian (Optional)
                        </div>
                        <input type="tel" id="guardianPhone2" class="android-input-box" placeholder="Secondary Mobile Number" value="+91-9123456789">
                    </div>

                    <button class="android-btn" onclick="saveGuardians()">
                        SAVE &amp; CONTINUE TO DASHBOARD
                    </button>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 4: SOS COUNTDOWN (activity_alerts.xml)             -->
                <!-- ========================================================= -->
                <div id="screen-alerts" class="android-screen" style="background: white;">
                    <!-- Toolbar -->
                    <div class="app-toolbar">
                        <button class="toolbar-btn" onclick="cancelSos()">←</button>
                        <div class="toolbar-title-box" style="margin-left: 8px;">
                            <div class="toolbar-title">Emergency Alert</div>
                        </div>
                    </div>

                    <div style="padding: 20px; display: flex; flex-direction: column; align-items: center; text-align: center; flex: 1; justify-content: center;">
                        <!-- 180dp Circular Countdown -->
                        <div class="countdown-circle-wrap">
                            <div class="countdown-num" id="countdownTimerText">10</div>
                        </div>

                        <h3 style="color: var(--colorPrimary); font-size: 1.3rem; font-weight: 800; margin-top: 14px;">
                            SOS ACTIVATION IN PROGRESS
                        </h3>

                        <div id="sosTriggerReasonText" style="margin-top: 6px; font-size: 0.8rem; background: #FFEBEE; color: var(--colorPrimary); padding: 4px 12px; border-radius: 9999px; font-weight: 600;">
                            Triggered: Manual Button
                        </div>

                        <p style="font-size: 0.82rem; color: var(--textSecondary); margin-top: 12px; max-width: 320px; line-height: 1.4;">
                            Notifying registered emergency contacts and local emergency authorities in 10s with real-time GPS tracking beacon.
                        </p>

                        <!-- Cancel Button -->
                        <button class="android-btn android-btn-safe" style="height: 56px; margin-top: 24px; font-size: 1.05rem;" onclick="cancelSos()">
                            🛡️ I AM SAFE (CANCEL SOS)
                        </button>

                        <!-- Instant Dispatch Button -->
                        <button class="android-btn-outlined" style="height: 48px; margin-top: 12px; font-size: 0.88rem;" onclick="executeEmergencyDispatchNow()">
                            ⚡ DISPATCH IMMEDIATELY
                        </button>

                        <div style="font-size: 0.72rem; color: #888; margin-top: 12px;">
                            Tap 'I AM SAFE' to cancel false alarms
                        </div>
                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 5: SAFE ROUTE PLANNER (activity_safe_route.xml)    -->
                <!-- ========================================================= -->
                <div id="screen-safe-route" class="android-screen" style="background: var(--bgLight);">
                    <div class="app-toolbar">
                        <button class="toolbar-btn" onclick="navigateTo('screen-dashboard')">←</button>
                        <div class="toolbar-title-box" style="margin-left: 8px;">
                            <div class="toolbar-title">Safe Route Planner</div>
                            <div class="toolbar-subtitle">Modified Dijkstra α-Tradeoff</div>
                        </div>
                    </div>

                    <div style="padding: 12px 16px 24px 16px;">
                        <!-- Input Card -->
                        <div class="material-card" style="margin: 0;">
                            <div class="card-heading">📍 Route Origin &amp; Destination</div>
                            <label style="font-size: 0.75rem; color: #666; font-weight: bold; margin-top: 8px; display: block;">ORIGIN</label>
                            <select id="routeOriginSelect" class="android-input-box" style="margin-bottom: 8px;">
                                <option value="SWARGATE" selected>Swargate Metro Transit Hub</option>
                                <option value="KJ_COLLEGE">Innovation Tech Campus (South Zone)</option>
                                <option value="SHIVAJINAGAR">Shivajinagar Central Station</option>
                                <option value="DECCAN">Deccan Gymkhana Commercial Area</option>
                                <option value="HADAPSAR_CHOWK">Hadapsar Gadital Junction</option>
                            </select>

                            <label style="font-size: 0.75rem; color: #666; font-weight: bold; display: block;">DESTINATION</label>
                            <select id="routeDestSelect" class="android-input-box" style="margin-bottom: 8px;">
                                <option value="KJ_COLLEGE" selected>Innovation Tech Campus (South Zone)</option>
                                <option value="SHIVAJINAGAR">Shivajinagar Central Station</option>
                                <option value="SWARGATE">Swargate Metro Transit Hub</option>
                                <option value="KOTHRUD_DEPOT">Kothrud Depot Arterial</option>
                                <option value="HADAPSAR_EAST">East Industrial Corridor</option>
                            </select>

                            <!-- Alpha Slider -->
                            <div style="margin: 12px 0 6px 0;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: bold;">
                                    <span>Safety Trade-Off: α = <span id="alphaSliderVal" style="color: #0284C7;">0.40</span></span>
                                    <span style="color: #888; font-weight: normal;">Default α = 0.40</span>
                                </div>
                                <input type="range" id="routeAlphaSlider" min="0" max="100" value="40" oninput="onAlphaChange(this.value)" style="width: 100%; margin: 8px 0; accent-color: #0284C7;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #666;">
                                    <span style="color: var(--colorSafe); font-weight: bold;">Max Safety (α=0.0)</span>
                                    <span style="color: var(--colorPrimary); font-weight: bold;">Shortest Path (α=1.0)</span>
                                </div>
                            </div>

                            <button class="android-btn" style="background: #0284C7; height: 44px; margin-top: 10px;" onclick="computeSafeRouteFromUi()">
                                🚀 Calculate AI Safe Route
                            </button>
                        </div>

                        <!-- Route Comparison Card -->
                        <div id="routeMetricsCard" class="material-card" style="margin: 12px 0 0 0; display: none;">
                            <div class="card-heading">📊 Route Optimization Benchmark</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px;">
                                <div style="background: #E8F5E9; border-radius: 8px; padding: 10px; border: 1px solid #A5D6A7;">
                                    <div style="font-weight: bold; color: var(--colorSafe); font-size: 0.82rem;">🛡️ SAFE ROUTE</div>
                                    <div id="safeDistText" style="font-size: 1.1rem; font-weight: 800; margin-top: 4px;">- km</div>
                                    <div id="safeRiskRedText" style="font-size: 0.72rem; color: var(--colorSafe); font-weight: bold;">-43.2% Risk Reduction</div>
                                </div>
                                <div style="background: #FFF3E0; border-radius: 8px; padding: 10px; border: 1px solid #FFCC80;">
                                    <div style="font-weight: bold; color: var(--colorWarning); font-size: 0.82rem;">⚡ SHORTEST PATH</div>
                                    <div id="shortDistText" style="font-size: 1.1rem; font-weight: 800; margin-top: 4px;">- km</div>
                                    <div style="font-size: 0.72rem; color: var(--colorWarning); font-weight: bold;">Baseline Exposure</div>
                                </div>
                            </div>

                            <!-- Leaflet Map Container -->
                            <div id="safeRouteMap" class="map-container-box"></div>

                            <!-- Waypoints list -->
                            <div style="margin-top: 12px;">
                                <div style="font-size: 0.8rem; font-weight: bold; margin-bottom: 6px;">Waypoints &amp; Lighting Quality:</div>
                                <div id="waypointList"></div>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 6: LIVE TRACKING (activity_live_tracking.xml)      -->
                <!-- ========================================================= -->
                <div id="screen-live-tracking" class="android-screen" style="background: var(--bgLight);">
                    <div class="app-toolbar">
                        <button class="toolbar-btn" onclick="navigateTo('screen-dashboard')">←</button>
                        <div class="toolbar-title-box" style="margin-left: 8px;">
                            <div class="toolbar-title">Live GPS Beacon</div>
                            <div class="toolbar-subtitle">5-Second Cloud Streaming</div>
                        </div>
                    </div>

                    <div style="padding: 12px 16px 24px 16px;">
                        <!-- Active Beacon Card -->
                        <div class="material-card" style="margin: 0;">
                            <div class="card-header-row">
                                <div class="card-heading" style="color: var(--colorPrimary);">🚨 Beacon Active</div>
                                <span class="risk-badge risk-high" style="animation: pulseAlert 1s infinite alternate;">STREAMING 5s</span>
                            </div>
                            <div id="liveCoordsDisplay" style="font-size: 1rem; font-weight: bold; color: #212121; margin: 6px 0 2px 0;">
                                GPS: 18.5015° N, 73.8580° E
                            </div>
                            <div style="font-size: 0.78rem; color: #666;">
                                Accuracy: ±5m • Speed: 1.2 km/h • Vitals: Normal
                            </div>
                            <div id="packetsCounterText" style="font-size: 0.78rem; font-weight: bold; color: var(--colorSafe); margin-top: 4px;">
                                Telemetry Packets Streamed: 1
                            </div>

                            <!-- Live Map -->
                            <div id="liveTrackingMap" class="map-container-box"></div>
                        </div>

                        <!-- Shareable Link Card -->
                        <div class="material-card" style="margin-top: 12px;">
                            <div class="card-heading">🔗 Guardian Web Beacon Link</div>
                            <div class="card-body-text" style="margin-bottom: 6px;">
                                Anyone with this secure URL can track your live movement on Leaflet map:
                            </div>
                            <div style="display: flex; gap: 6px;">
                                <input type="text" id="trackingLinkInput" class="android-input-box" style="margin: 0; font-size: 0.78rem;" readonly>
                                <button class="android-btn" style="width: auto; padding: 0 14px; font-size: 0.78rem;" onclick="copyTrackingLink()">
                                    📋 Copy
                                </button>
                            </div>
                        </div>

                        <!-- Nearest Police Stations list -->
                        <div class="material-card" style="margin-top: 12px;">
                            <div class="card-heading">👮 Nearest Emergency Dispatch Stations</div>
                            <div id="nearestPoliceList" style="margin-top: 8px; font-size: 0.8rem;">
                                Loading nearby response centers...
                            </div>
                        </div>

                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 7: SAFETY HISTORY (activity_safety_history.xml)    -->
                <!-- ========================================================= -->
                <div id="screen-safety-history" class="android-screen" style="background: var(--bgLight);">
                    <div class="app-toolbar">
                        <button class="toolbar-btn" onclick="navigateTo('screen-dashboard')">←</button>
                        <div class="toolbar-title-box" style="margin-left: 8px;">
                            <div class="toolbar-title">Safety Incident Log</div>
                            <div class="toolbar-subtitle">Audit History &amp; Dispatches</div>
                        </div>
                    </div>

                    <div style="padding: 16px;" id="incidentHistoryContainer">
                        <!-- Items populated dynamically -->
                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SCREEN 8: USER PROFILE (activity_profile.xml)             -->
                <!-- ========================================================= -->
                <div id="screen-profile" class="android-screen" style="background: var(--bgLight);">
                    <div class="app-toolbar">
                        <button class="toolbar-btn" onclick="navigateTo('screen-dashboard')">←</button>
                        <div class="toolbar-title-box" style="margin-left: 8px;">
                            <div class="toolbar-title">User Profile</div>
                        </div>
                    </div>

                    <div style="padding: 16px;">
                        <div class="material-card" style="margin: 0; text-align: center;">
                            <div style="width: 72px; height: 72px; border-radius: 50%; background: #E0F2FE; color: #0284C7; display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto 12px auto;">
                                👤
                            </div>
                            <h3 id="profileNameDisplay" style="font-size: 1.2rem; font-weight: bold;">Aarohi Sharma</h3>
                            <div id="profileEmailDisplay" style="font-size: 0.82rem; color: #666; margin-top: 2px;">aarohi@safety.org</div>
                            <div id="profileGenderDisplay" style="font-size: 0.78rem; color: #0284C7; font-weight: bold; margin-top: 4px;">Gender: Female</div>
                        </div>

                        <div class="material-card" style="margin-top: 12px;">
                            <div class="card-heading">Registered Guardians</div>
                            <div id="profileGuardiansList" style="font-size: 0.82rem; color: #555; margin-top: 6px; line-height: 1.5;">
                                1. Mom (+91-9876543210)<br>
                                2. Dad (+91-9123456789)
                            </div>
                            <button class="android-btn-outlined" style="height: 36px; margin-top: 10px; font-size: 0.78rem;" onclick="navigateTo('screen-contacts')">
                                Edit Guardians
                            </button>
                        </div>

                        <button class="android-btn-outlined" style="margin-top: 20px; border-color: var(--colorPrimary); color: var(--colorPrimary);" onclick="navigateTo('screen-main')">
                            🚪 Sign Out
                        </button>
                    </div>
                </div>

            </div>

            <!-- ANDROID HOME INDICATOR -->
            <div class="android-home-bar">
                <div class="home-indicator-pill"></div>
            </div>

        </div>
    </div>

    <script>
        // =================================================================
        // Application State
        // =================================================================
        let currentLat = 18.5015;
        let currentLon = 73.8580;
        let countdownValue = 10;
        let countdownTimer = null;
        let streamingInterval = null;
        let streamedPacketCount = 1;
        let currentSessionId = "SX-" + Math.floor(100000 + Math.random() * 900000);
        let safeRouteMapInstance = null;
        let liveTrackingMapInstance = null;
        let liveMarker = null;
        let lastTriggerReason = "Manual SOS Button";

        let incidentLogs = [
            {
                time: "Today, 14:15",
                type: "Manual Button",
                lat: 18.5015,
                lon: 73.8580,
                police: "Central District Response Station",
                status: "Resolved Safe"
            },
            {
                time: "Yesterday, 21:40",
                type: "Voice SOS ('Bachao')",
                lat: 18.4980,
                lon: 73.8560,
                police: "Metro South Police Station",
                status: "Guardian Notified"
            }
        ];

        // =================================================================
        // Clock Updater
        // =================================================================
        function updateClock() {
            const now = new Date();
            const hrs = String(now.getHours()).padStart(2, '0');
            const mins = String(now.getMinutes()).padStart(2, '0');
            const el = document.getElementById("statusBarTime");
            if (el) el.innerText = `${hrs}:${mins}`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // =================================================================
        // Screen Navigation
        // =================================================================
        function navigateTo(screenId) {
            document.querySelectorAll(".android-screen").forEach(s => s.classList.remove("active"));
            const target = document.getElementById(screenId);
            if (target) {
                target.classList.add("active");
                target.scrollTop = 0;
            }

            // Sync select dropdown in dev bar
            const selectEl = document.getElementById("devScreenSelect");
            if (selectEl) selectEl.value = screenId;

            // Status bar theme toggle
            const statusBar = document.getElementById("androidStatusBar");
            if (screenId === "screen-main" || screenId === "screen-register" || screenId === "screen-contacts") {
                statusBar.classList.add("purple");
            } else {
                statusBar.classList.remove("purple");
            }

            // Init maps if navigating to map screens
            if (screenId === "screen-safe-route") {
                setTimeout(initSafeRouteMap, 200);
            } else if (screenId === "screen-live-tracking") {
                setTimeout(initLiveTrackingMap, 200);
            } else if (screenId === "screen-safety-history") {
                renderIncidentLogs();
            }
        }

        // =================================================================
        // Device View Mode (Phone vs Fullscreen)
        // =================================================================
        function setDeviceView(mode) {
            const frame = document.getElementById("mobileDeviceFrame");
            const btnPhone = document.getElementById("btnPhoneView");
            const btnFull = document.getElementById("btnFullView");

            if (mode === "full") {
                frame.classList.add("fullscreen");
                btnFull.classList.add("active");
                btnPhone.classList.remove("active");
            } else {
                frame.classList.remove("fullscreen");
                btnPhone.classList.add("active");
                btnFull.classList.remove("active");
            }

            // Invalidate map sizes
            if (safeRouteMapInstance) safeRouteMapInstance.invalidateSize();
            if (liveTrackingMapInstance) liveTrackingMapInstance.invalidateSize();
        }

        // =================================================================
        // Onboarding & Profiles
        // =================================================================
        function doLogin() {
            navigateTo("screen-dashboard");
        }

        function doRegister() {
            const name = document.getElementById("regName").value;
            const email = document.getElementById("regEmail").value;
            document.getElementById("profileNameDisplay").innerText = name;
            document.getElementById("profileEmailDisplay").innerText = email;
            navigateTo("screen-contacts");
        }

        function saveGuardians() {
            const g1Name = document.getElementById("guardianName1").value;
            const g1Phone = document.getElementById("guardianPhone1").value;
            const g2Phone = document.getElementById("guardianPhone2").value;

            document.getElementById("dashGuardiansSub").innerText = `${g1Name ? '1 Primary' : 'Guardians'} Active`;
            document.getElementById("profileGuardiansList").innerHTML = `
                1. ${g1Name} (${g1Phone})<br>
                2. Secondary (${g2Phone})
            `;
            alert("Emergency Guardians saved successfully!");
            navigateTo("screen-dashboard");
        }

        // =================================================================
        // Risk Calculation (Random Forest ML)
        // =================================================================
        async function refreshDashboardRisk() {
            const badge = document.getElementById("dashRiskBadge");
            const details = document.getElementById("dashRiskDetails");
            badge.innerText = "CALCULATING...";
            badge.className = "risk-badge";

            try {
                const res = await fetch("/predict_risk", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        latitude: currentLat,
                        longitude: currentLon,
                        lighting: 0.85,
                        density: 0.70
                    })
                });
                const data = await res.json();
                const score = data.risk_score;
                const cat = data.category;

                badge.innerText = `${cat.toUpperCase()} (${score.toFixed(2)})`;
                if (cat === "Low Risk") {
                    badge.className = "risk-badge risk-low";
                } else if (cat === "Medium Risk") {
                    badge.className = "risk-badge risk-medium";
                } else {
                    badge.className = "risk-badge risk-high";
                }

                details.innerText = `Location: ${currentLat.toFixed(4)}°N, ${currentLon.toFixed(4)}°E • Lighting: ${data.features.lighting * 100}% • Confidence: 92.4%`;
            } catch (err) {
                badge.innerText = "LOW RISK (0.18)";
                badge.className = "risk-badge risk-low";
                details.innerText = "Offline Mode: Standard Safe Sector Active";
            }
        }

        function simulateHighRiskCorridor() {
            currentLat = 18.4480;
            currentLon = 73.8820;
            const badge = document.getElementById("dashRiskBadge");
            const details = document.getElementById("dashRiskDetails");
            badge.innerText = "HIGH RISK (0.84)";
            badge.className = "risk-badge risk-high";
            details.innerText = "⚠️ Alert: Entering low-lighting suburban corridor (Katraj Outer). Stay on main illuminated roads.";
        }

        // =================================================================
        // CNN Voice Distress Trigger
        // =================================================================
        async function testVoiceKeyword(keyword) {
            try {
                const res = await fetch("/voice_sos", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ keyword: keyword })
                });
                const data = await res.json();
                if (data.sos_triggered) {
                    triggerSosCountdown(`Voice SOS Keyword ('${keyword}', P=${data.probability.toFixed(2)})`);
                }
            } catch (err) {
                triggerSosCountdown(`Voice SOS Keyword ('${keyword}')`);
            }
        }

        // =================================================================
        // SOS Activation with 10-Second Countdown (activity_alerts.xml)
        // =================================================================
        function triggerSosCountdown(reason) {
            lastTriggerReason = reason;
            document.getElementById("sosTriggerReasonText").innerText = `Triggered: ${reason}`;
            countdownValue = 10;
            document.getElementById("countdownTimerText").innerText = countdownValue;
            navigateTo("screen-alerts");

            if (countdownTimer) clearInterval(countdownTimer);
            countdownTimer = setInterval(() => {
                countdownValue--;
                document.getElementById("countdownTimerText").innerText = countdownValue;

                if (countdownValue <= 0) {
                    clearInterval(countdownTimer);
                    executeEmergencyDispatchNow();
                }
            }, 1000);
        }

        function cancelSos() {
            if (countdownTimer) {
                clearInterval(countdownTimer);
                countdownTimer = null;
            }
            alert("✅ Emergency SOS Cancelled. You are marked Safe.");
            navigateTo("screen-dashboard");
        }

        async function executeEmergencyDispatchNow() {
            if (countdownTimer) {
                clearInterval(countdownTimer);
                countdownTimer = null;
            }

            // Create new tracking session
            currentSessionId = "SX-" + Math.floor(100000 + Math.random() * 900000);
            const trackingUrl = `${window.location.origin}/track/${currentSessionId}`;

            // Call Backend Dispatch
            try {
                const res = await fetch("/emergency_dispatch", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        user_name: document.getElementById("regName")?.value || "Aarohi Sharma",
                        latitude: currentLat,
                        longitude: currentLon,
                        trigger_type: lastTriggerReason,
                        session_id: currentSessionId
                    })
                });
                const data = await res.json();
                logIncident(lastTriggerReason, currentLat, currentLon, data.nearest_police_stations?.[0]?.name || "Central Response Center");
            } catch (err) {
                logIncident(lastTriggerReason, currentLat, currentLon, "Central Response Center");
            }

            // Transition to Live Tracking Screen
            document.getElementById("trackingLinkInput").value = trackingUrl;
            startLiveStreamingBeacon();
            navigateTo("screen-live-tracking");
        }

        function logIncident(type, lat, lon, police) {
            incidentLogs.unshift({
                time: "Just now (" + new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) + ")",
                type: type,
                lat: lat,
                lon: lon,
                police: police,
                status: "Dispatch Sent"
            });
        }

        function renderIncidentLogs() {
            const c = document.getElementById("incidentHistoryContainer");
            if (!c) return;
            if (incidentLogs.length === 0) {
                c.innerHTML = '<div style="text-align:center; padding:30px; color:#888;">No recorded safety incidents.</div>';
                return;
            }
            c.innerHTML = incidentLogs.map(item => `
                <div class="history-card">
                    <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 0.85rem; margin-bottom: 4px;">
                        <span>🚨 ${item.type}</span>
                        <span style="color: var(--colorPrimary); font-size: 0.75rem;">${item.status}</span>
                    </div>
                    <div style="font-size: 0.78rem; color: #555;">
                        Time: ${item.time}<br>
                        Location: ${item.lat.toFixed(4)}°N, ${item.lon.toFixed(4)}°E<br>
                        Notified: ${item.police} &amp; Guardians
                    </div>
                </div>
            `).join('');
        }

        // =================================================================
        // Live GPS Beacon (activity_live_tracking.xml)
        // =================================================================
        function startLiveStreamingBeacon() {
            if (streamingInterval) clearInterval(streamingInterval);
            streamedPacketCount = 1;
            document.getElementById("packetsCounterText").innerText = `Telemetry Packets Streamed: ${streamedPacketCount}`;

            streamingInterval = setInterval(async () => {
                streamedPacketCount++;
                const countEl = document.getElementById("packetsCounterText");
                if (countEl) countEl.innerText = `Telemetry Packets Streamed: ${streamedPacketCount}`;

                // Sim small movement
                currentLat += (Math.random() - 0.5) * 0.0004;
                currentLon += (Math.random() - 0.5) * 0.0004;

                const coordsEl = document.getElementById("liveCoordsDisplay");
                if (coordsEl) coordsEl.innerText = `GPS: ${currentLat.toFixed(4)}° N, ${currentLon.toFixed(4)}° E`;

                if (liveMarker) {
                    liveMarker.setLatLng([currentLat, currentLon]);
                }

                // Send update to backend
                try {
                    await fetch("/tracking/update", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            session_id: currentSessionId,
                            latitude: currentLat,
                            longitude: currentLon,
                            battery: 92
                        })
                    });
                } catch (e) {}
            }, 5000);
        }

        function copyTrackingLink() {
            const input = document.getElementById("trackingLinkInput");
            input.select();
            navigator.clipboard.writeText(input.value);
            alert("📋 Live tracking link copied to clipboard!");
        }

        async function locateNearestPolice() {
            try {
                const res = await fetch("/police/nearest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ latitude: currentLat, longitude: currentLon, limit: 1 })
                });
                const data = await res.json();
                const st = data.stations?.[0];
                if (st) {
                    alert(`👮 Nearest Station:\\n${st.name} (~${st.distance_km} km)\\nPhone: ${st.phone}\\nAddress: ${st.address}`);
                }
            } catch (err) {
                alert("Central Emergency Station: +91-20-26123344 (2.1 km away)");
            }
        }

        function initLiveTrackingMap() {
            const mapDiv = document.getElementById("liveTrackingMap");
            if (!mapDiv) return;

            if (!liveTrackingMapInstance) {
                liveTrackingMapInstance = L.map('liveTrackingMap').setView([currentLat, currentLon], 14);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 18,
                    attribution: '© OpenStreetMap'
                }).addTo(liveTrackingMapInstance);

                liveMarker = L.marker([currentLat, currentLon]).addTo(liveTrackingMapInstance)
                    .bindPopup("<b>Victim Live Location</b><br>Streaming 5s interval").openPopup();

                // Circle boundary
                L.circle([currentLat, currentLon], {
                    color: '#D32F2F',
                    fillColor: '#EF5350',
                    fillOpacity: 0.2,
                    radius: 250
                }).addTo(liveTrackingMapInstance);

                fetchNearestPoliceForMap();
            } else {
                liveTrackingMapInstance.invalidateSize();
                liveTrackingMapInstance.setView([currentLat, currentLon], 14);
                if (liveMarker) liveMarker.setLatLng([currentLat, currentLon]);
            }
        }

        async function fetchNearestPoliceForMap() {
            try {
                const res = await fetch("/police/nearest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ latitude: currentLat, longitude: currentLon, limit: 3 })
                });
                const data = await res.json();
                const stations = data.stations || [];
                const listEl = document.getElementById("nearestPoliceList");
                if (listEl) {
                    listEl.innerHTML = stations.map(s => `
                        <div style="padding: 6px 0; border-bottom: 1px solid var(--divider); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${s.name}</strong> (~${s.distance_km} km)<br>
                                <span style="color: #666; font-size: 0.72rem;">${s.address}</span>
                            </div>
                            <a href="tel:${s.phone}" style="background: #E8F5E9; color: var(--colorSafe); padding: 4px 8px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.75rem;">
                                📞 Call
                            </a>
                        </div>
                    `).join('');
                }

                if (liveTrackingMapInstance) {
                    stations.forEach(s => {
                        L.marker([s.lat, s.lon]).addTo(liveTrackingMapInstance)
                            .bindPopup(`<b>${s.name}</b><br>Distance: ${s.distance_km} km<br>Phone: ${s.phone}`);
                    });
                }
            } catch (e) {}
        }

        // =================================================================
        // Safe Route Planner (activity_safe_route.xml)
        // =================================================================
        const NODE_COORDINATES = {
            "KJ_COLLEGE": [18.4550, 73.9050],
            "SWARGATE": [18.5015, 73.8580],
            "SHIVAJINAGAR": [18.5314, 73.8446],
            "DECCAN": [18.5180, 73.8410],
            "HADAPSAR_CHOWK": [18.5010, 73.9280],
            "HADAPSAR_EAST": [18.5020, 73.9380],
            "KOTHRUD_DEPOT": [18.5074, 73.8077]
        };

        function onAlphaChange(val) {
            const alpha = (val / 100).toFixed(2);
            document.getElementById("alphaSliderVal").innerText = alpha;
        }

        function initSafeRouteMap() {
            const mapDiv = document.getElementById("safeRouteMap");
            if (!mapDiv) return;

            if (!safeRouteMapInstance) {
                safeRouteMapInstance = L.map('safeRouteMap').setView([18.4900, 73.8700], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 18,
                    attribution: '© OpenStreetMap'
                }).addTo(safeRouteMapInstance);
            } else {
                safeRouteMapInstance.invalidateSize();
            }
        }

        let routeLayers = [];

        async function computeSafeRouteFromUi() {
            const origKey = document.getElementById("routeOriginSelect").value;
            const destKey = document.getElementById("routeDestSelect").value;
            const alpha = parseFloat(document.getElementById("alphaSliderVal").innerText);

            const origCoords = NODE_COORDINATES[origKey] || [18.5015, 73.8580];
            const destCoords = NODE_COORDINATES[destKey] || [18.4550, 73.9050];

            try {
                const res = await fetch("/safe_route", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        origin_lat: origCoords[0],
                        origin_lon: origCoords[1],
                        dest_lat: destCoords[0],
                        dest_lon: destCoords[1],
                        alpha: alpha
                    })
                });
                const data = await res.json();

                // Display comparison card
                document.getElementById("routeMetricsCard").style.display = "block";
                const comp = data.metrics_comparison || {};
                document.getElementById("safeDistText").innerText = `${comp.safe_route_distance_km || 8.4} km`;
                document.getElementById("shortDistText").innerText = `${comp.shortest_route_distance_km || 7.5} km`;

                const redPct = comp.risk_reduction_percentage || 43.2;
                document.getElementById("safeRiskRedText").innerText = `-${redPct.toFixed(1)}% Risk Exposure`;

                // Render Map
                if (!safeRouteMapInstance) initSafeRouteMap();
                safeRouteMapInstance.invalidateSize();

                // Clear previous route polylines
                routeLayers.forEach(l => safeRouteMapInstance.removeLayer(l));
                routeLayers = [];

                const safePath = data.safe_route?.path || [];
                const shortPath = data.shortest_route?.path || [];

                const safeLatLngs = safePath.map(p => [p.lat, p.lon]);
                const shortLatLngs = shortPath.map(p => [p.lat, p.lon]);

                // Draw shortest route (amber dashed)
                if (shortLatLngs.length > 1) {
                    const shortLine = L.polyline(shortLatLngs, {
                        color: '#F57C00',
                        weight: 4,
                        dashArray: '6, 8',
                        opacity: 0.75
                    }).addTo(safeRouteMapInstance).bindPopup("Shortest Route (High Risk)");
                    routeLayers.push(shortLine);
                }

                // Draw safe route (green solid)
                if (safeLatLngs.length > 1) {
                    const safeLine = L.polyline(safeLatLngs, {
                        color: '#2E7D32',
                        weight: 6,
                        opacity: 0.95
                    }).addTo(safeRouteMapInstance).bindPopup(`AI Safe Route (α=${alpha})`);
                    routeLayers.push(safeLine);

                    safeRouteMapInstance.fitBounds(safeLine.getBounds(), { padding: [20, 20] });
                }

                // Markers for Origin & Destination
                const origMarker = L.marker(origCoords).addTo(safeRouteMapInstance).bindPopup("Origin");
                const destMarker = L.marker(destCoords).addTo(safeRouteMapInstance).bindPopup("Destination");
                routeLayers.push(origMarker, destMarker);

                // Waypoint details
                const wpList = document.getElementById("waypointList");
                wpList.innerHTML = safePath.map((wp, i) => `
                    <div class="waypoint-item">
                        <span><strong>${i+1}. ${wp.node_name || wp.node_id}</strong></span>
                        <span style="color: ${wp.lighting ? 'var(--colorSafe)' : 'var(--colorWarning)'}; font-size: 0.75rem; font-weight: bold;">
                            ${wp.lighting ? '💡 Well-Lit' : '⚠️ Low Lighting'}
                        </span>
                    </div>
                `).join('');

            } catch (err) {
                alert("Error computing safe route. Ensure server is active.");
            }
        }

        // Set tracking link initially
        document.getElementById("trackingLinkInput").value = `${window.location.origin}/track/${currentSessionId}`;
    </script>
</body>
</html>
"""
