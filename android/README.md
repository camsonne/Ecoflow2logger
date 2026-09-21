# EcoFlow Logger (Android)

A standalone Android app version of this repo's Python logger: each user
enters their own EcoFlow Open API credentials, the app polls their device
in the background, and shows the same kind of charge/power dashboard the
Python project renders as a static chart — but running entirely on-device,
for anyone who installs it, with no shared backend and no GitHub involved.

## Why it exists

The Python project's polling relies on GitHub Actions, which only one
person can practically configure and run for their own device (repo
secrets, a Pages dashboard, etc.). This app lets any EcoFlow user run the
same kind of polling loop themselves, from their phone, using their own
credentials — see the multi-user discussion that led here for the
alternatives that were considered and why this one won.

## Project structure

```
android/
  core/    plain Kotlin/JVM module: EcoFlow API signing, HTTP client, quota
           parsing. No Android dependency at all — ported from
           ecoflow_logger/{api,metrics}.py, including the extra-battery
           slot-resolution fix. Compiles and runs its tests with a plain
           JDK, no Android SDK required.
  app/     the actual Android app: Settings screen (enter credentials),
           Dashboard screen (stat tiles + a SoC chart), a WorkManager
           background poller, and encrypted local credential storage.
           Requires the Android SDK to build.
```

## Important: what's been verified and what hasn't

This was written in a sandboxed environment whose network policy blocks
`dl.google.com` — the actual Android SDK distribution point — while still
allowing Maven Central and (partially) `maven.google.com`. In practice
that means:

- **`:core` is for real.** It was actually compiled and its 19 unit tests
  actually run, in this repo's own CI-equivalent process, including a
  mutation check that reinstates the extra-battery bug and confirms the
  regression test fails against it. Run it yourself with:
  ```bash
  cd android
  ./gradlew :core:test --configure-on-demand
  ```
  (`--configure-on-demand` matters here for the same reason it did while
  writing this: without it, Gradle configures `:app` too, which needs the
  Android SDK even just to be *evaluated*. Once you have Android Studio /
  the SDK installed, you don't need that flag for anything.)

- **`:app` has never been compiled.** Every file in it was written
  carefully, cross-checked against known-correct API shapes, and read back
  looking specifically for invented APIs — two were actually caught and
  fixed this way (a `Result` naming collision between Kotlin's own
  `kotlin.Result` and WorkManager's `ListenableWorker.Result`, and two
  places where a nonexistent helper was called instead of grabbing
  `LocalContext.current`). But static reading is not a compiler. **The
  first real build of `:app` will be whatever happens when you open this
  folder in Android Studio.** Expect to fix at least a small thing —
  most likely a dependency version Android Studio's Upgrade Assistant
  offers to bump for you.

## Building

1. Install [Android Studio](https://developer.android.com/studio) (it
   bundles the SDK).
2. Open the `android/` folder as a project.
3. Let Gradle sync — this is where any dependency version issues will
   surface, with an actionable error message and usually a one-click fix.
4. Run on a device or emulator.

## Before publishing to Google Play

- **Change the package name.** `applicationId` in `app/build.gradle.kts`
  is currently `com.ecoflowlogger.app`, a placeholder. It must be globally
  unique on the Play Store.
- **Add a launcher icon.** None is set — Android Studio's *New > Image
  Asset* wizard handles this in under a minute; the repo's existing
  `icons/icon-512.png` (used for the PWA dashboard) is reasonable source
  art if you want visual continuity.
- **Create a Google Play Developer account** ($25 one-time fee) and a
  privacy policy — required for any app that handles user-entered
  credentials, even when (as here) they never leave the device.
- Consider whether you want `isMinifyEnabled = true` for the release
  build once you've verified R8/ProGuard doesn't strip anything the app
  needs (WorkManager and Compose both have known consumer ProGuard rules
  bundled in their AARs, so this is usually safe, but verify before
  shipping).

## How polling works

- `PollWorker` (a `CoroutineWorker`) calls the same `EcoFlowClient` /
  `Metrics.extractReading` logic as the Python project, then appends the
  reading to a JSON-lines file in app-private storage via `ReadingsStore`
  — the same append-only philosophy as `ecoflow_logger.logger`'s CSV, just
  JSON instead of CSV since that's a more natural fit for Kotlin's
  `org.json`.
- `WorkScheduler` enqueues that worker as unique periodic work. **Android
  will not run periodic background work more often than every 15
  minutes**, regardless of what's requested — there's no way around this
  without a persistent foreground service (a permanently-visible
  notification, and more Play Store scrutiny), which this app
  deliberately doesn't use.
- Credentials live in `SettingsRepository`, backed by
  `EncryptedSharedPreferences` rather than plain `SharedPreferences` —
  the secret key is a live credential and shouldn't sit in plaintext on
  disk.

## Tests

```bash
cd android
./gradlew :core:test --configure-on-demand
```

Covers: HMAC-SHA256 request signing (parameter ordering, sorting,
flattening — ported from `test_api.py`), quota field extraction including
every case in `test_metrics.py`, and a mocked HTTP round-trip through
`EcoFlowClient` (success, an API error code, and constructor validation).
