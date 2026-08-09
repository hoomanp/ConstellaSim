# ConstellaSim Mobile (iOS + Android)

Capacitor shell that launches the ConstellaSim Flask mobile UI on a phone or simulator.

## Prerequisites

- Node.js 20+
- Backend running on your LAN (`python3 mobile_client/app.py`, port **5001**)
- **iOS:** macOS + Xcode 15+
- **Android:** Android Studio (API 24+)

## Quick start

```bash
# 1) Backend (repo root)
export FLASK_SECRET_KEY=dev-secret
export PORT=5001
python3 mobile_client/app.py

# 2) Native shell
cd mobile
npm install
npx cap sync
```

### iOS

```bash
npx cap open ios
# In Xcode: select a simulator or device → Run
```

On a physical iPhone, enter your Mac’s LAN IP in the launcher (e.g. `192.168.1.42`) and tap **Connect & Launch**.  
In the iOS Simulator, tap **Local** (`127.0.0.1`) then connect. If GPS is unavailable, use **Demo Mode** in the web UI.

### Android

```bash
npx cap open android
# Android Studio → Run on emulator or device
```

Emulator: tap **Local** (uses `10.0.2.2` → host machine).  
Device: enter the PC’s LAN IP, same Wi‑Fi as the Flask host.

## What this shell does

1. Shows a dark launcher to pick backend host/port
2. Probes `GET /api/health`
3. Navigates into the Flask UI so sessions, SSE, and relative `/api/*` paths work unchanged
4. Declares location + cleartext LAN permissions for GPS diagnostics

## Project layout

```
mobile/
├── capacitor.config.ts
├── package.json
├── www/index.html          # launcher
├── ios/                    # Xcode project (after npm install / cap add)
└── android/                # Android Studio project (after npm install / cap add)
```

## App IDs

| Platform | ID |
|---|---|
| Bundle / applicationId | `com.constellasim.app` |
| Display name | ConstellaSim |
