pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "EcoFlowLogger"

// :core has no Android dependency and builds as plain Kotlin/JVM, so it
// compiles and runs its unit tests anywhere a JDK is available. :app is a
// real Android application module and requires the Android SDK (Android
// Studio, or a CI runner with the SDK installed) to build.
include(":core")
include(":app")
