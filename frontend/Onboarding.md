# First-run UI preview

The guided setup is opt-in. Without a recognized `NSPB_ONBOARDING_DEMO` value, the app opens the existing launcher exactly as before. The preview never instantiates `BuildModel`, detects tools, reads selected files, installs anything or opens the App Store. Its exit screen stands in for opening the library.

From the repository root, enter `frontend`, then run one scenario:

```sh
cd frontend
NSPB_ONBOARDING_DEMO=fresh swift run
NSPB_ONBOARDING_DEMO=xcodeReady swift run
NSPB_ONBOARDING_DEMO=keysInvalid swift run
NSPB_ONBOARDING_DEMO=xcodeFailed swift run
NSPB_ONBOARDING_DEMO=noGames swift run
```

- `fresh`: Start, select a platform, Continue, Get Xcode, wait, Finish setup, confirm the found keys, review the games, Continue, Open library.
- `xcodeReady`: the same path, with Xcode already present; its checks tick through automatically.
- `keysInvalid`: confirming the found file fails validation. Choose or drop another file to exercise recovery. The mock does not read it.
- `xcodeFailed`: setup fails with a plain explanation and expandable diagnostics. Retry, then Finish setup to recover.
- `noGames`: the mock folder scan finds no NSPs and shows a hint. Use Back or Set up later.

Set up later preserves an in-memory snapshot; Resume setup restores it. Persistence across app launches is deliberately left to the real driver.

## Wiring contract

`OnboardingView<Driver: OnboardingDriver>` observes a driver on the main actor. A real `ObservableObject` should publish `OnboardingState` as one value and implement these intents:

```swift
start()
choosePlatform(_ platform: OnboardingPlatform)
getXcode()
finishXcodeSetup()
retry(_ step: OnboardingStep)
chooseKeys(_ url: URL)
confirmKeys()
chooseGames(_ url: URL)
back()
next()
skipForLater()
openLibrary()
```

The driver owns detection, installation, privileges, security-scoped access to selected URLs, validation, decoded cover images, persistence, and navigation. The view owns only presentation, the system chooser, drop URL decoding, disclosure expansion and input handling. No key file contents belong in `OnboardingState`, failure text or diagnostics. Failure messages must already be localized; `details` is diagnostic text supplied by the driver.

Use `OnboardingState.next()` and `.back()` for gated navigation. `canAdvance` requires disk space on Welcome, a platform selection, Xcode plus all background tasks, valid keys, or a nonempty games list respectively. `primary` distinguishes a step action (Get Xcode, Finish setup, confirm keys, Retry) from advancing. `primaryEnabled` also gates completion and dismissed flows. `setupTasks` derives the iOS row from the selected platform.

Automatic advancement belongs in the driver. The mock gives completed Xcode and keys a brief checkmark hold, then advances. Returning to an already completed step stays there so Back remains useful. Games wait for explicit Continue so the player can review what was found. On a return visit, selecting iPhone after completed Mac setup adds the iOS preparation step.

Persist the current step and selections before handling `skipForLater`; inject the restored state on the next launch and revalidate external prerequisites in the real driver. `MockOnboardingDriver(state:)` demonstrates restoration without preferences or file I/O. Its `animated: false` initializer disables scheduled changes for deterministic tests.

## Presentation choices

The flow retains the launcher's dark appearance, palette, Manrope, cream capsule primary button, secondary button style and 1.8:1 cover crop. The app currently forces dark mode, so onboarding does too. The welcome icon is the app's own (`NSApp.applicationIconImage` inside the .app, a symbol under `swift run`); there is no SwiftPM resource, because the release workflow copies only the executable. Background preparation stays beside Xcode, while a fixed footer keeps the primary action visible at the launcher's 900 × 680 minimum window size. Long content scrolls.

Return activates the primary action, Escape and controller B go back. Every interactive element has an onboarding controller target. Step headings receive VoiceOver focus, and changing status is announced. Reduced Motion replaces slides with fades, shows completed checks immediately, stops indeterminate loops and disables progress interpolation.

## Validation

```sh
swift build -c release
swift test
NX_ONBOARDING_CAPTURE_DIR="$PWD/.build/onboarding-captures" swift test --filter OnboardingTests
```

The last command optionally captures all six screens at minimum window size in English and Simplified Chinese. It only hosts mock SwiftUI views. The normal suite skips that capture unless requested.

Files added: `OnboardingState.swift`, `MockOnboardingDriver.swift`, `OnboardingView.swift`, `OnboardingTests.swift`, and this note. Files changed: `NSPortBuilderApp.swift` (demo branch) and `Localization.swift` (both languages).
