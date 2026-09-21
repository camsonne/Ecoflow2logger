plugins {
    kotlin("jvm") version "1.9.24"
}

// Repositories are centralized in settings.gradle.kts
// (dependencyResolutionManagement), not declared per-module.

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.json:json:20240303")

    testImplementation(kotlin("test"))
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
}

tasks.test {
    useJUnitPlatform()
}

// Targets JVM 17 bytecode (via the compiler's -jvm-target flag, no actual
// JDK 17 toolchain required) so this module's classes stay consumable by
// :app once Android tooling is available, without forcing a toolchain
// download in environments -- like this one -- that only have a newer JDK
// installed and no route to fetch another.
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}
tasks.withType<JavaCompile>().configureEach {
    sourceCompatibility = "17"
    targetCompatibility = "17"
}
