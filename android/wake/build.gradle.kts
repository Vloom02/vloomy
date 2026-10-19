import org.jetbrains.kotlin.gradle.dsl.JvmTarget

// Kotlin puro (sin Android) para poder probar el wake word en la PC con onnxruntime de escritorio.
// Usa la misma API ai.onnxruntime que onnxruntime-android, que pone la app.
plugins {
    id("org.jetbrains.kotlin.jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }
}

dependencies {
    compileOnly("com.microsoft.onnxruntime:onnxruntime:1.20.0")
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.20.0")
    testImplementation("junit:junit:4.13.2")
}
