package com.aarjoo.surakshax;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.cardview.widget.CardView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class SafetyHistoryActivity extends AppCompatActivity {

    public static final String PREF_KEY_HISTORY = "safety_history_records";
    private LinearLayout llContainer;
    private TextView tvCount;

    public static void logIncident(Context context, String triggerSource, double lat, double lon, String nearestPolice) {
        SharedPreferences prefs = context.getSharedPreferences(Contacts.PREFS_NAME, Context.MODE_PRIVATE);
        String currentJson = prefs.getString(PREF_KEY_HISTORY, "[]");
        try {
            JSONArray arr = new JSONArray(currentJson);
            JSONObject obj = new JSONObject();
            obj.put("id", "INC-" + (System.currentTimeMillis() % 1000000));
            obj.put("timestamp", System.currentTimeMillis());
            obj.put("date_str", new SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(new Date()));
            obj.put("trigger", triggerSource);
            obj.put("latitude", lat);
            obj.put("longitude", lon);
            obj.put("police", nearestPolice);
            obj.put("status", "Alert Dispatched (Carrier & Police)");

            // Prepend new incident
            JSONArray newArr = new JSONArray();
            newArr.put(obj);
            for (int i = 0; i < arr.length() && i < 30; i++) {
                newArr.put(arr.get(i));
            }
            prefs.edit().putString(PREF_KEY_HISTORY, newArr.toString()).apply();
        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_safety_history);

        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }
        toolbar.setNavigationOnClickListener(v -> finish());

        llContainer = findViewById(R.id.llIncidentContainer);
        tvCount = findViewById(R.id.tvIncidentCount);

        findViewById(R.id.btnClearHistory).setOnClickListener(v -> {
            getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE)
                    .edit().putString(PREF_KEY_HISTORY, "[]").apply();
            renderHistory();
            Toast.makeText(this, "Incident logs cleared", Toast.LENGTH_SHORT).show();
        });

        seedInitialLogsIfEmpty();
        renderHistory();
    }

    private void seedInitialLogsIfEmpty() {
        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        if (!prefs.contains(PREF_KEY_HISTORY) || prefs.getString(PREF_KEY_HISTORY, "[]").equals("[]")) {
            logIncident(this, "High-Risk Corridor Entry Warning", 18.5020, 73.9380, "Hadapsar Police Station");
            logIncident(this, "CNN Voice Trigger (Bachao)", 18.4550, 73.9050, "Kondhwa Police Station");
        }
    }

    private void renderHistory() {
        llContainer.removeAllViews();
        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        String rawJson = prefs.getString(PREF_KEY_HISTORY, "[]");

        try {
            JSONArray arr = new JSONArray(rawJson);
            tvCount.setText(arr.length() + " Recorded Incidents");

            if (arr.length() == 0) {
                TextView empty = new TextView(this);
                empty.setText("No safety incidents recorded.\nSystem in continuous background monitoring mode.");
                empty.setGravity(android.view.Gravity.CENTER);
                empty.setPadding(0, 80, 0, 0);
                empty.setTextColor(Color.GRAY);
                empty.setTextSize(16f);
                llContainer.addView(empty);
                return;
            }

            for (int i = 0; i < arr.length(); i++) {
                JSONObject obj = arr.getJSONObject(i);
                View card = createIncidentCard(obj);
                llContainer.addView(card);
            }
        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    private View createIncidentCard(JSONObject obj) throws JSONException {
        CardView card = new CardView(this);
        card.setCardElevation(4f);
        card.setRadius(12f);
        card.setUseCompatPadding(true);

        LinearLayout inner = new LinearLayout(this);
        inner.setOrientation(LinearLayout.VERTICAL);
        inner.setPadding(20, 20, 20, 20);

        // Header (ID + Date)
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);

        TextView tvId = new TextView(this);
        tvId.setText("🚨 " + obj.optString("id", "INC-001"));
        tvId.setTextSize(16f);
        tvId.setTextColor(Color.parseColor("#D32F2F"));
        tvId.setTypeface(null, android.graphics.Typeface.BOLD);
        tvId.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        TextView tvDate = new TextView(this);
        tvDate.setText(obj.optString("date_str", ""));
        tvDate.setTextSize(12f);
        tvDate.setTextColor(Color.DKGRAY);

        header.addView(tvId);
        header.addView(tvDate);
        inner.addView(header);

        // Trigger Source
        TextView tvTrigger = new TextView(this);
        tvTrigger.setText("Trigger: " + obj.optString("trigger", "Manual SOS"));
        tvTrigger.setTextSize(14f);
        tvTrigger.setTextColor(Color.BLACK);
        tvTrigger.setPadding(0, 10, 0, 4);
        tvTrigger.setTypeface(null, android.graphics.Typeface.BOLD);
        inner.addView(tvTrigger);

        // Location & Police
        double lat = obj.optDouble("latitude", 0.0);
        double lon = obj.optDouble("longitude", 0.0);
        String police = obj.optString("police", "Nearest Police Station");

        TextView tvLoc = new TextView(this);
        tvLoc.setText("GPS: " + String.format(Locale.US, "%.4f, %.4f", lat, lon) + " • " + police);
        tvLoc.setTextSize(13f);
        tvLoc.setTextColor(Color.DKGRAY);
        inner.addView(tvLoc);

        // Status badge & Map button
        LinearLayout footer = new LinearLayout(this);
        footer.setOrientation(LinearLayout.HORIZONTAL);
        footer.setPadding(0, 12, 0, 0);

        TextView tvStatus = new TextView(this);
        tvStatus.setText("✓ " + obj.optString("status", "Resolved"));
        tvStatus.setTextSize(12f);
        tvStatus.setTextColor(Color.parseColor("#2E7D32"));
        tvStatus.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button btnMap = new Button(this);
        btnMap.setText("View Map");
        btnMap.setTextSize(12f);
        btnMap.setOnClickListener(v -> {
            String uri = "geo:" + lat + "," + lon + "?q=" + lat + "," + lon + "(Incident+Location)";
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(uri)));
        });

        footer.addView(tvStatus);
        footer.addView(btnMap);
        inner.addView(footer);

        card.addView(inner);
        return card;
    }
}
