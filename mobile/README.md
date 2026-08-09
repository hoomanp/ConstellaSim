# ConstellaSim Mobile (iOS + Android)

Capacitor shell that launches the **v2 FastAPI + React** demo UI on a phone or simulator.

## Prerequisites

- Node.js 20+
- Backend: `python -m api.main` on port **5001** (after `cd web && npm run build`)
- **iOS:** macOS + Xcode 15+
- **Android:** Android Studio (API 24+)

## Quick start

```bash
# Backend (repo root) — serves API + built React UI
./scripts/demo.sh

# Native shell
cd mobile
npm install
npx cap sync
npx cap open ios      # or android
```

Enter the laptop LAN IP in the launcher (or **Local** on simulator/emulator).

Bundle ID: `com.constellasim.app`
