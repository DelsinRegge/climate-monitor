package com.example.climatemonitor;

import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The only screen of the app: it shows temperature and humidity,
 * lets you turn the device on/off and set the temperature threshold.
 * The data comes from the REST API on the Raspberry Pi (see the backend folder).
 *
 * To keep things simple it uses only the standard HttpURLConnection,
 * without third-party libraries (Retrofit/OkHttp can be added later).
 */
public class MainActivity extends AppCompatActivity {

    private static final long REFRESH_MS = 5000; // auto-refresh every 5 seconds

    private EditText etServer;
    private EditText etThreshold;
    private TextView tvTemperature;
    private TextView tvHumidity;
    private TextView tvDevice;
    private TextView tvAlert;
    private TextView tvStatus;

    // Network requests must not run on the main thread, so we use a separate thread.
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler uiHandler = new Handler(Looper.getMainLooper());
    private final Runnable autoRefresh = new Runnable() {
        @Override
        public void run() {
            refresh();
            uiHandler.postDelayed(this, REFRESH_MS);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        etServer = findViewById(R.id.etServer);
        etThreshold = findViewById(R.id.etThreshold);
        tvTemperature = findViewById(R.id.tvTemperature);
        tvHumidity = findViewById(R.id.tvHumidity);
        tvDevice = findViewById(R.id.tvDevice);
        tvAlert = findViewById(R.id.tvAlert);
        tvStatus = findViewById(R.id.tvStatus);

        Button btnRefresh = findViewById(R.id.btnRefresh);
        Button btnOn = findViewById(R.id.btnOn);
        Button btnOff = findViewById(R.id.btnOff);
        Button btnSetThreshold = findViewById(R.id.btnSetThreshold);

        btnRefresh.setOnClickListener(v -> refresh());
        btnOn.setOnClickListener(v -> sendCommand("POST", "/device/on", null));
        btnOff.setOnClickListener(v -> sendCommand("POST", "/device/off", null));
        btnSetThreshold.setOnClickListener(v -> setThreshold());
    }

    @Override
    protected void onResume() {
        super.onResume();
        uiHandler.post(autoRefresh); // start auto-refresh while the screen is visible
    }

    @Override
    protected void onPause() {
        super.onPause();
        uiHandler.removeCallbacks(autoRefresh); // stop it when the app is minimized
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    /** Requests /sensors and updates the screen. */
    private void refresh() {
        executor.execute(() -> {
            try {
                String json = request("GET", "/sensors", null);
                JSONObject o = new JSONObject(json);
                runOnUiThread(() -> showSensors(o));
            } catch (Exception e) {
                showError(e);
            }
        });
    }

    /** Sends a command (turn the device on/off, set threshold) and refreshes the screen right away. */
    private void sendCommand(String method, String path, String body) {
        executor.execute(() -> {
            try {
                request(method, path, body);
            } catch (Exception e) {
                showError(e);
                return;
            }
            refresh();
        });
    }

    private void setThreshold() {
        String text = etThreshold.getText().toString().trim().replace(',', '.');
        double value;
        try {
            value = Double.parseDouble(text);
        } catch (NumberFormatException e) {
            tvStatus.setText("Enter the threshold as a number, e.g. 28");
            return;
        }
        String body = String.format(Locale.US, "{\"value\": %.1f}", value);
        sendCommand("PUT", "/threshold", body);
    }

    // ---------- display ----------

    private void showSensors(JSONObject o) {
        tvTemperature.setText(String.format(Locale.getDefault(), "%.1f °C", o.optDouble("temperature")));
        tvHumidity.setText(String.format(Locale.getDefault(), "%.1f %%", o.optDouble("humidity")));
        tvDevice.setText(o.optBoolean("device_on") ? "Device: ON" : "Device: off");

        double threshold = o.optDouble("threshold");
        if (o.optBoolean("alert")) {
            tvAlert.setText(String.format(Locale.getDefault(),
                    "⚠ Temperature is above the threshold (%.1f °C)!", threshold));
            tvAlert.setTextColor(Color.parseColor("#C62828"));
        } else {
            tvAlert.setText(String.format(Locale.getDefault(),
                    "Temperature is normal (threshold %.1f °C)", threshold));
            tvAlert.setTextColor(Color.parseColor("#2E7D32"));
        }
        tvStatus.setText("Updated: " + o.optString("timestamp"));
    }

    private void showError(Exception e) {
        runOnUiThread(() -> tvStatus.setText("No connection to the server: " + e.getMessage()));
    }

    // ---------- HTTP ----------

    /** Performs an HTTP request to the server and returns the response body. Do NOT call from the main thread. */
    private String request(String method, String path, String jsonBody) throws Exception {
        String base = etServer.getText().toString().trim();
        if (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        HttpURLConnection conn = (HttpURLConnection) new URL(base + path).openConnection();
        try {
            conn.setRequestMethod(method);
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(4000);
            conn.setRequestProperty("Accept", "application/json");

            if (jsonBody != null) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");
                try (OutputStream out = conn.getOutputStream()) {
                    out.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                }
            }

            int code = conn.getResponseCode();
            InputStream stream = (code >= 200 && code < 300) ? conn.getInputStream() : conn.getErrorStream();
            String text = readAll(stream);
            if (code < 200 || code >= 300) {
                throw new Exception("HTTP " + code + " " + text);
            }
            return text;
        } finally {
            conn.disconnect();
        }
    }

    private static String readAll(InputStream stream) throws Exception {
        if (stream == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
        }
        return sb.toString();
    }
}
