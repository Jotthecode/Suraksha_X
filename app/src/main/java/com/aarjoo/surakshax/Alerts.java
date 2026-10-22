package com.aarjoo.surakshax;

import android.Manifest;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.telephony.SmsManager;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.app.ActivityCompat;

import com.android.volley.Request;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FirebaseFirestore;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

public class Alerts extends AppCompatActivity {

    private TextView tvCountdown;
    private CountDownTimer countDownTimer;
    private boolean isSafePressed = false;
    private boolean isDispatched = false;

    private double lat = 18.4550;
    private double lon = 73.9050;
    private String triggerReason = "Manual SOS Button";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_alerts);

        // Ensure SMS permission
        ActivityCompat.requestPermissions(
                this,
                new String[]{Manifest.permission.SEND_SMS, Manifest.permission.CALL_PHONE},
                102
        );

        lat = getIntent().getDoubleExtra("lat", 18.4550);
        lon = getIntent().getDoubleExtra("lon", 73.9050);
        triggerReason = getIntent().getStringExtra("trigger_reason");
        if (triggerReason == null || triggerReason.isEmpty()) {
            triggerReason = "Emergency SOS Button";
        }

        // Toolbar
        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }
        toolbar.setNavigationOnClickListener(v -> abortAlert());

        tvCountdown = findViewById(R.id.tvCountdown);

        // 10-second fail-safe countdown timer matching paper Section III-B (5)
        countDownTimer = new CountDownTimer(10000, 1000) {
            @Override
            public void onTick(long millisUntilFinished) {
                tvCountdown.setText(String.valueOf(millisUntilFinished / 1000));
            }

            @Override
            public void onFinish() {
                if (!isSafePressed && !isDispatched) {
                    tvCountdown.setText("0");
                    executeEmergencyDispatch();
                }
            }
        }.start();

        // Safe Button (Cancel Alert)
        Button btnSafe = findViewById(R.id.btnSafe);
        btnSafe.setOnClickListener(v -> abortAlert());

        // Instant Dispatch Button
        Button btnInstant = findViewById(R.id.btnInstantDispatch);
        btnInstant.setOnClickListener(v -> {
            if (countDownTimer != null) countDownTimer.cancel();
            executeEmergencyDispatch();
        });
    }

    private void abortAlert() {
        isSafePressed = true;
        if (countDownTimer != null) {
            countDownTimer.cancel();
        }
        Toast.makeText(this, "SOS Alert Cancelled - False Alarm", Toast.LENGTH_SHORT).show();
        startActivity(new Intent(Alerts.this, Happy_Screen.class));
        finish();
    }

    private void executeEmergencyDispatch() {
        if (isDispatched) return;
        isDispatched = true;

        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        String userName = prefs.getString(Register_Activity.KEY_USER_NAME, "Registered User");
        String contactPhone1 = prefs.getString(Contacts.KEY_GUARDIAN_PHONE, "9302414220");
        String contactPhone2 = prefs.getString(Contacts.KEY_GUARDIAN_PHONE_2, "");
        String contactName1 = prefs.getString(Contacts.KEY_GUARDIAN_NAME, "Primary Guardian");

        // 1. Dispatch multi-channel alert via backend REST API (Section IV-E)
        JSONObject payload = new JSONObject();
        try {
            payload.put("user_name", userName);
            payload.put("latitude", lat);
            payload.put("longitude", lon);
            payload.put("trigger_reason", triggerReason);

            JSONArray contactsArr = new JSONArray();
            JSONObject c1 = new JSONObject();
            c1.put("name", contactName1);
            c1.put("phone", contactPhone1);
            c1.put("relation", "Guardian");
            contactsArr.put(c1);

            if (!contactPhone2.isEmpty()) {
                JSONObject c2 = new JSONObject();
                c2.put("name", "Secondary Guardian");
                c2.put("phone", contactPhone2);
                c2.put("relation", "Guardian");
                contactsArr.put(c2);
            }
            payload.put("contacts", contactsArr);

        } catch (JSONException e) {
            e.printStackTrace();
        }

        JsonObjectRequest dispatchRequest = new JsonObjectRequest(
                Request.Method.POST,
                Config.getEmergencyDispatchUrl(this),
                payload,
                response -> {
                    String sessionId = response.optString("tracking_session_id", "");
                    String trackingUrl = response.optString("live_tracking_url", "");

                    Toast.makeText(this, "Emergency Dispatch Complete! Live tracking started.", Toast.LENGTH_LONG).show();

                    // Log to Safety History
                    SafetyHistoryActivity.logIncident(this, triggerReason, lat, lon, "Assigned Nearest Police Station");

                    // Transition to Screen 6: Live Tracking Share Screen
                    Intent trackingIntent = new Intent(Alerts.this, LiveTrackingActivity.class);
                    trackingIntent.putExtra("session_id", sessionId);
                    startActivity(trackingIntent);
                    finish();
                },
                error -> {
                    // Fallback to local carrier SMS if backend is unreachable
                    sendLocalCarrierSmsFallback(contactPhone1, contactPhone2, userName);

                    SafetyHistoryActivity.logIncident(this, triggerReason, lat, lon, "Local Carrier SMS Dispatched");

                    Intent trackingIntent = new Intent(Alerts.this, LiveTrackingActivity.class);
                    startActivity(trackingIntent);
                    finish();
                }
        );

        Volley.newRequestQueue(this).add(dispatchRequest);

        // 2. Cloud Firestore Logging (if online)
        try {
            FirebaseUser user = FirebaseAuth.getInstance().getCurrentUser();
            Map<String, Object> alertLog = new HashMap<>();
            alertLog.put("userId", user != null ? user.getUid() : "offline_client");
            alertLog.put("userName", userName);
            alertLog.put("latitude", lat);
            alertLog.put("longitude", lon);
            alertLog.put("trigger", triggerReason);
            alertLog.put("status", "DISPATCHED");
            alertLog.put("timestamp", System.currentTimeMillis());

            FirebaseFirestore.getInstance()
                    .collection("emergency_alerts")
                    .add(alertLog);
        } catch (Exception ignored) {}
    }

    private void sendLocalCarrierSmsFallback(String phone1, String phone2, String userName) {
        String mapsLink = "https://www.google.com/maps?q=" + lat + "," + lon;
        String message = "🚨 EMERGENCY! " + userName + " triggered SurakshaX SOS. Location: " + mapsLink;

        try {
            SmsManager smsManager = SmsManager.getDefault();
            if (phone1 != null && !phone1.isEmpty()) {
                smsManager.sendTextMessage(phone1, null, message, null, null);
            }
            if (phone2 != null && !phone2.isEmpty()) {
                smsManager.sendTextMessage(phone2, null, message, null, null);
            }
            Toast.makeText(this, "Carrier SMS Dispatched!", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (countDownTimer != null) {
            countDownTimer.cancel();
        }
    }
}