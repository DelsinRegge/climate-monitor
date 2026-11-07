# Android app (Java)

This folder contains only the source of the screen. Create the Android Studio project yourself
(so you get the right Gradle and SDK versions), then copy these two files into it.

## Steps

1. Android Studio -> **New Project** -> template **Empty Views Activity**.
   - Name: `ClimateMonitor`
   - Package name: `com.example.climatemonitor`
   - Language: **Java**
2. Replace the contents of these files in the new project with the files from this folder:
   - `app/src/main/java/com/example/climatemonitor/MainActivity.java`
   - `app/src/main/res/layout/activity_main.xml`
3. Open `app/src/main/AndroidManifest.xml` and make **two** changes:
   ```xml
   <!-- 1) Internet permission: OUTSIDE the <application> tag, next to it -->
   <uses-permission android:name="android.permission.INTERNET" />

   <!-- 2) Allow plain HTTP (no https) - add this attribute to the <application> tag -->
   <application
       android:usesCleartextTraffic="true"
       ... the other attributes stay as they were ...>
   ```
4. Run the app (emulator or phone).

## Which server address to enter

| Where the app runs | Address |
|---|---|
| Android Studio emulator, server on the same computer | `http://10.0.2.2:8000` (default) |
| Real phone, server on a computer or Raspberry Pi in the same Wi-Fi network | `http://<IP address>:8000`, e.g. `http://192.168.1.50:8000` |

You can change the address directly on the app screen.

## How it works

- `MainActivity.java` requests `GET /sensors` every 5 seconds, shows temperature and humidity
  and highlights a warning when the temperature is above the threshold.
- The "Turn on" / "Turn off" buttons call `POST /device/on` and `POST /device/off`.
- The "Set" button calls `PUT /threshold`.
- HTTP requests run in a separate thread (Android does not allow network calls on the main thread).
