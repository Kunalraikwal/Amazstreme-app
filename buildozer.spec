[app]

# App information
title = Amazstreme
package.name = amazstreme
package.domain = org.amazstreme
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,kv,ttf,sqlite,mp4,db

# Requirements
requirements = 
    python3,
    kivy==2.2.1,
    plyer,
    openssl,
    sqlite3,
    requests,
    ffpyplayer  # For better video support

# Android-specific
android.permissions = 
    INTERNET,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    ACCESS_NETWORK_STATE,
    WAKE_LOCK,
    RECORD_AUDIO  # Needed for video playback

android.api = 31
android.minapi = 21
android.ndk = 23b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a  # 64-bit and 32-bit support

# Kivy configuration
orientation = portrait
fullscreen = 0
log_level = 2

# Presplash and icon (replace with your files)
icon.filename = assets/icon.png
presplash.filename = assets/presplash.png

# Build settings
android.allow_backup = True
android.wakelock = True  # Keep screen on during playback

# Add directories for videos and downloads
source.include_patterns = videos/*,downloads/*

# Gradle dependencies (for modern Android support)
android.gradle_dependencies =
    androidx.appcompat:appcompat:1.6.1,
    androidx.media:media:1.6.0

# Enable AndroidX
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1