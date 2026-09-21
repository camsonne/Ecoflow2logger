// Intentionally empty. :core and :app each declare their own plugin
// versions directly (rather than via a root-level `apply false` version
// catalog), so that requesting `:core:test --configure-on-demand` never
// forces Gradle to resolve the Android Gradle Plugin -- which needs the
// Android SDK -- just to configure a build that doesn't touch :app.
