# ConstellaSim Mobile (iOS + Android)

Native Capacitor shells that embed the **React mission console** and talk to the FastAPI backend over LAN.

## Prerequisites

| Platform | Needs |
|---|---|
| Both | Node 20+, backend `python -m api.main` on `:5001` |
| Android | Android Studio / SDK 35 (debug APK builds in CI-like Linux) |
| iOS | **macOS + Xcode 15+** + CocoaPods (`pod install`) |

## Sync & open

```bash
# Terminal A — API (same Wi‑Fi as the phone)
./scripts/demo.sh

# Terminal B — embed UI + sync native projects
./scripts/mobile-sync.sh
cd mobile
npx cap open android   # or: npx cap open ios
```

### First launch on device / emulator
1. Tap **⚙ Settings**
2. Set API base URL:
   - Android emulator: `http://10.0.2.2:5001`
   - iOS Simulator: `http://127.0.0.1:5001`
   - Physical device: `http://<your-laptop-LAN-IP>:5001`
3. **Save & reconnect** → run **Demo mode**

### Android debug APK (this environment verified)
```bash
cd mobile/android
./gradlew assembleDebug
# → app/build/outputs/apk/debug/app-debug.apk
```

### iOS (Mac only)
```bash
cd mobile/ios/App
pod install
open App.xcworkspace
# Run on Simulator or device; allow Location when prompted
```

## Features covered in the native shell
- Demo / GPS diagnostic (Capacitor Geolocation when available)
- Live topology map + SSE AI stream
- NL planner, chat, optimizer, briefing download
- Anomaly alerts (`POST /api/alerts/evaluate` after each run)
- Backend URL settings for LAN demos

Bundle ID: `com.constellasim.app`
