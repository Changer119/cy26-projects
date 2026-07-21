plugins {
    id("com.android.application")
}

android {
    namespace = "com.phone2computer.transfer"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.phone2computer.transfer"
        minSdk = 29
        targetSdk = 36
        versionCode = 3
        versionName = "2.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:5.4.0")
    testImplementation("junit:junit:4.13.2")
}
