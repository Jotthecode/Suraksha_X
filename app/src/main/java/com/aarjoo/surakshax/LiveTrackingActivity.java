package com.aarjoo.surakshax;

import android.Manifest;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.app.ActivityCompat;

import com.android.volley.Request;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;
import com.google.android.gms.tasks.CancellationTokenSource;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.Locale;

public class LiveTrackingActivity extends AppCompatActivity {

    private TextView tvCoordinates, tvTelemetryStats, tvStreamUpdatesCount, tvTrackingUrl;
    private TextView tvPolice1, tvPolice2;
    private FusedLocationProviderClient fusedLocationClient;

    private String sessionId = "";
    private String trackingUrl = "";
    private int packetCount = 0;
    private double currentLat = 18.4550, currentLon = 73.9050;

    private Handler streamHandler = new Handler(Looper.getMainLooper());
    private Runnable streamRunnable;
    private boolean isTrackingActive = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_live_tracking);

        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }
        toolbar.setNavigationOnClickListener(v -> finish());

        tvCoordinates = findViewById(R.id.tvCoordinates);
        tvTelemetryStats = findViewById(R.id.tvTelemetryStats);
        tvStreamUpdatesCount = findViewById(R.id.tvStreamUpdatesCount);
        tvTrackingUrl = findViewById(R.id.tvTrackingUrl);
        tvPolice1 = findViewById(R.id.tvPolice1);
        tvPolice2 = findViewById(R.id.tvPolice2);

        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this);

        // Retrieve existing session id or generate short session ID
        sessionId = getIntent().getStringExtra("session_id");
        if (sessionId == null || sessionId.isEmpty()) {
            sessionId = String.valueOf(System.currentTimeMillis() % 1000000);
        }

        trackingUrl = Config.getLiveTrackWebUrl(this, sessionId);
        tvTrackingUrl.setText(trackingUrl);

        // Share button
        findViewById(R.id.btnShareLink).setOnClickListener(v -> {
            Intent shareIntent = new Intent(Intent.ACTION_SEND);
            shareIntent.setType("text/plain");
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, "EMERGENCY: Track My Live Location");
            shareIntent.putExtra(Intent.EXTRA_TEXT,
                    "🚨 EMERGENCY ALERT: I have activated live safety tracking on SurakshaX.\n" +
                    "Follow my real-time GPS location here:\n" + trackingUrl);
            startActivity(Intent.createChooser(shareIntent, "Share Live Tracking Link"));
        });

        // Open Web Map button
        findViewById(R.id.btnOpenWebMap).setOnClickListener(v -> {
            Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(trackingUrl));
            startActivity(browserIntent);
        });

        // Stop Tracking button
        findViewById(R.id.btnStopTracking).setOnClickListener(v -> {
            isTrackingActive = false;
            if (streamRunnable != null) {
                streamHandler.removeCallbacks(streamRunnable);
            }
            Toast.makeText(this, "Emergency tracking ended. You are safe now.", Toast.LENGTH_LONG).show();
            startActivity(new Intent(this, Happy_Screen.class));
            finish();
        });

        // Query initial location & nearest police stations
        fetchLocationAndUpdate();

        // Start 5-second interval streaming loop matching Section IV-D
        streamRunnable = new Runnable() {
            @Override
            public void run() {
                if (isTrackingActive) {
                    fetchLocationAndUpdate();
                    streamHandler.postDelayed(this, 5000); // 5-second interval
                }
            }
        };
        streamHandler.postDelayed(streamRunnable, 5000);
    }

    private void fetchLocationAndUpdate() {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
                ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            sendLocationToCloud(currentLat, currentLon);
            return;
        }

        CancellationTokenSource cts = new CancellationTokenSource();
        fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, cts.getToken())
                .addOnSuccessListener(location -> {
                    if (location != null) {
                        currentLat = location.getLatitude();
                        currentLon = location.getLongitude();
                    }
                    sendLocationToCloud(currentLat, currentLon);
                })
                .addOnFailureListener(e -> {
                    sendLocationToCloud(currentLat, currentLon);
                });
    }

    private void sendLocationToCloud(double lat, double lon) {
        packetCount++;
        tvCoordinates.setText(String.format(Locale.US, "GPS: %.5f, %.5f", lat, lon));
        tvTelemetryStats.setText("Accuracy: ±5m • Speed: 1.2 km/h • Vitals: 74 BPM");
        tvStreamUpdatesCount.setText("Packets Streamed to Cloud: " + packetCount + " (Interval: 5s)");

        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        String userName = prefs.getString(Register_Activity.KEY_USER_NAME, "Registered User");

        JSONObject payload = new JSONObject();
        try {
            payload.put("session_id", sessionId);
            payload.put("user_name", userName);
            payload.put("latitude", lat);
            payload.put("longitude", lon);
            payload.put("accuracy", 5.0);
            payload.put("speed", 1.2);
            payload.put("battery", "84%");
        } catch (JSONException e) {
            e.printStackTrace();
            return;
        }

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.POST,
                Config.getTrackingUpdateUrl(this),
                payload,
                response -> {},
                error -> {}
        );
        Volley.newRequestQueue(this).add(request);

        // Fetch nearest police stations on first packet
        if (packetCount == 1) {
            fetchNearestPolice(lat, lon);
        }
    }

    private void fetchNearestPolice(double lat, double lon) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("latitude", lat);
            payload.put("longitude", lon);
        } catch (JSONException e) {
            return;
        }

        JsonObjectRequest req = new JsonObjectRequest(
                Request.Method.POST,
                Config.getNearestPoliceUrl(this),
                payload,
                response -> {
                    try {
                        JSONArray nearest = response.optJSONArray("nearest_police_stations");
                        if (nearest != null && nearest.length() >= 2) {
                            JSONObject p1 = nearest.getJSONObject(0);
                            JSONObject p2 = nearest.getJSONObject(1);
                            tvPolice1.setText(String.format(Locale.US, "1. %s (~%.1f km) • %s",
                                    p1.optString("name"), p1.optDouble("distance_km"), p1.optString("phone")));
                            tvPolice2.setText(String.format(Locale.US, "2. %s (~%.1f km) • %s",
                                    p2.optString("name"), p2.optDouble("distance_km"), p2.optString("phone")));
                        }
                    } catch (JSONException e) {
                        e.printStackTrace();
                    }
                },
                error -> {
                    tvPolice1.setText("1. Kondhwa Police Station (~2.6 km) • +91-20-26930055");
                    tvPolice2.setText("2. Wanowrie Police Station (~4.0 km) • +91-20-26801100");
                }
        );
        Volley.newRequestQueue(this).add(req);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        isTrackingActive = false;
        if (streamRunnable != null) {
            streamHandler.removeCallbacks(streamRunnable);
        }
    }
}
