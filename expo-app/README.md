# ConstellaSim via Expo Go (Mac mini)

This is a thin **Expo** shell that opens the ConstellaSim web mission console inside a WebView. It works with **Expo Go** — no Xcode native build required for day-to-day demos.

## One-time setup on the Mac mini

```bash
# Terminal A — backend + React UI
cd ConstellaSim
./scripts/demo.sh
# leave running on http://0.0.0.0:5001
```

```bash
# Terminal B — Expo
cd ConstellaSim/expo-app
npm install
npx expo start
```

Scan the QR code with **Expo Go** (iPhone/Android), or press `i` for iOS Simulator / `a` for Android emulator.

## Backend URL inside the app

| Device | URL to enter |
|---|---|
| iOS Simulator | `http://127.0.0.1:5001` |
| Android Emulator | `http://10.0.2.2:5001` |
| Physical phone (Expo Go) | `http://<Mac-mini-LAN-IP>:5001` |

Find your Mac LAN IP: **System Settings → Network**, or:

```bash
ipconfig getifaddr en0
```

Phone and Mac must be on the **same Wi‑Fi**. Then tap **Open in Expo Go** → use **Demo mode** in the mission console.

## Notes

- Expo Go loads this project; Capacitor (`mobile/`) remains available for store-style builds.
- The WebView hosts the same FastAPI-served React UI as the browser.
- Cleartext HTTP is enabled for LAN demos only.
