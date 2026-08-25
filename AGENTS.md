# AGENTS.md — Password Manager (Vault)

## Standing rule: permission-gated APIs must be declared AND runtime-tested

Whenever you add or modify code that uses **network, location, camera, microphone, storage, contacts, biometrics, or any other permission-gated API**, you MUST:

1. **Declare the matching permission** in the platform manifest:
   - Android: `mobile/android/app/src/main/AndroidManifest.xml` — e.g. `<uses-permission android:name="android.permission.INTERNET" />`, `ACCESS_NETWORK_STATE`, `CAMERA`, `READ_MEDIA_IMAGES`, `ACCESS_FINE_LOCATION`, etc.
   - iOS: `mobile/ios/Runner/Info.plist` — e.g. `NSCameraUsageDescription`, `NSLocationWhenInUseUsageDescription`, etc.
2. **Verify at runtime** — a missing permission **does not cause a build error**, only a runtime failure (e.g. `SocketException`, black camera preview). After adding the permission:
   - Rebuild the app (`flutter build apk` or `flutter run`)
   - Verify with `aapt dump permissions build/app/outputs/flutter-apk/app-release.apk | grep android.permission.INTERNET`
   - Trigger a **real** permission-gated call (e.g. `POST /api/auth/login` for `INTERNET`) and confirm success — do not just check that the build compiles.
3. **Add the permission to code review checklist** — call it out in PR description.

### Why this rule exists
`2026-08-23` The release APK shipped without `android.permission.INTERNET`. It compiled, installed, and rendered the login screen, but every `ApiClient` call in `mobile/lib/api.dart:88-123` failed with `SocketException: Connection refused` / `Cannot reach server`. Fix was a single line in `mobile/android/app/src/main/AndroidManifest.xml:2`. Lesson: always runtime-test network/auth flows after manifest changes.

### Project conventions
- Backend: FastAPI + SQLAlchemy, `backend/app/main.py:28`, `backend/app/config.py:9`. Env via `backend/.env` (copy from `.env.example`). Audit log and AES-256-GCM encryption enforced server-side.
- Mobile: Flutter `mobile/lib/api.dart:24` `defaultServer = String.fromEnvironment('API_BASE_URL', defaultValue: 'https://vault-ywol.onrender.com')` — override via login "Change server" (collapsed) or Settings → Server (`mobile/lib/screens/login_screen.dart:38`, `settings_screen.dart:35`), persisted via `SharedPreferences` (`vault_server`). Also build-time override: `flutter build apk --dart-define=API_BASE_URL=http://192.168.1.10:8000` with `android:usesCleartextTraffic="true"` already set. Default stays `https://vault-ywol.onrender.com` for production.
- Roles enforced server-side (`backend/app/deps.py:34`), not just UI.
