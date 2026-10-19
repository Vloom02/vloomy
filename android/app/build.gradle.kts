plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.vloomy"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.vloomy"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }  // celulares reales; sin x86 achica el APK
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(project(":wake"))
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
}
