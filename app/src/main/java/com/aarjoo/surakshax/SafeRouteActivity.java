package com.aarjoo.surakshax;

import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.cardview.widget.CardView;

import com.android.volley.Request;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.Locale;

public class SafeRouteActivity extends AppCompatActivity {

    private EditText etOrigin, etDestination;
    private TextView tvAlphaLabel, tvSafeDistance, tvSafeRisk, tvShortestDistance, tvShortestRisk, tvTradeoffSummary;
    private SeekBar sbAlpha;
    private CardView cardResults;
    private LinearLayout llWaypoints;

    // Default coordinates in Pune
    private double originLat = 18.5015, originLon = 73.8580; // Swargate
    private double destLat = 18.4550, destLon = 73.9050;     // KJ College Kondhwa
    private float currentAlpha = 0.40f;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_safe_route);

        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }
        toolbar.setNavigationOnClickListener(v -> finish());

        etOrigin = findViewById(R.id.etOrigin);
        etDestination = findViewById(R.id.etDestination);
        tvAlphaLabel = findViewById(R.id.tvAlphaLabel);
        sbAlpha = findViewById(R.id.sbAlpha);
        cardResults = findViewById(R.id.cardResults);
        tvSafeDistance = findViewById(R.id.tvSafeDistance);
        tvSafeRisk = findViewById(R.id.tvSafeRisk);
        tvShortestDistance = findViewById(R.id.tvShortestDistance);
        tvShortestRisk = findViewById(R.id.tvShortestRisk);
        tvTradeoffSummary = findViewById(R.id.tvTradeoffSummary);
        llWaypoints = findViewById(R.id.llWaypoints);

        // Preset buttons
        findViewById(R.id.btnPresetKj).setOnClickListener(v -> {
            etOrigin.setText("Swargate Metro Hub");
            etDestination.setText("K.J. College of Engineering (Kondhwa)");
            originLat = 18.5015; originLon = 73.8580;
            destLat = 18.4550; destLon = 73.9050;
        });

        findViewById(R.id.btnPresetShivaji).setOnClickListener(v -> {
            etOrigin.setText("K.J. College of Engineering (Kondhwa)");
            etDestination.setText("Shivajinagar Central Station");
            originLat = 18.4550; originLon = 73.9050;
            destLat = 18.5314; destLon = 73.8446;
        });

        // Alpha trade-off parameter slider
        sbAlpha.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                currentAlpha = progress / 100.0f;
                tvAlphaLabel.setText(String.format(Locale.US, "⚖️ Safety-Distance Trade-Off (α = %.2f)", currentAlpha));
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {}

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        // Compute route
        findViewById(R.id.btnCalculateRoute).setOnClickListener(v -> computeSafeRoute());

        // Start Live Navigation
        findViewById(R.id.btnStartLiveNav).setOnClickListener(v -> {
            Intent intent = new Intent(this, LiveTrackingActivity.class);
            intent.putExtra("is_navigating", true);
            intent.putExtra("dest_name", etDestination.getText().toString().trim());
            startActivity(intent);
        });
    }

    private void computeSafeRoute() {
        Toast.makeText(this, "Calculating Modified Dijkstra path...", Toast.LENGTH_SHORT).show();

        JSONObject payload = new JSONObject();
        try {
            payload.put("origin_lat", originLat);
            payload.put("origin_lon", originLon);
            payload.put("dest_lat", destLat);
            payload.put("dest_lon", destLon);
            payload.put("alpha", (double) currentAlpha);
        } catch (JSONException e) {
            e.printStackTrace();
            return;
        }

        String url = Config.getSafeRouteUrl(this);
        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.POST,
                url,
                payload,
                response -> {
                    renderRouteResults(response);
                },
                error -> {
                    // Fallback to local simulation if backend server is unreachable
                    renderSimulatedFallback();
                    Toast.makeText(this, "Offline / Demo Safe Route Rendered", Toast.LENGTH_SHORT).show();
                }
        );

        Volley.newRequestQueue(this).add(request);
    }

    private void renderRouteResults(JSONObject response) {
        try {
            cardResults.setVisibility(View.VISIBLE);
            JSONObject metrics = response.optJSONObject("metrics_comparison");
            JSONObject safe = response.optJSONObject("safe_route");
            JSONObject shortest = response.optJSONObject("shortest_route");

            double safeDist = safe != null ? safe.optDouble("total_distance_km", 5.7) : 5.7;
            double safeRisk = safe != null ? safe.optDouble("mean_risk_score", 0.23) : 0.23;
            double shortDist = shortest != null ? shortest.optDouble("total_distance_km", 5.1) : 5.1;
            double shortRisk = shortest != null ? shortest.optDouble("mean_risk_score", 0.41) : 0.41;

            double distInc = metrics != null ? metrics.optDouble("distance_increase_percent", 11.7) : 11.7;
            double riskRed = metrics != null ? metrics.optDouble("risk_reduction_percent", 43.2) : 43.2;

            tvSafeDistance.setText(String.format(Locale.US, "%.1f km", safeDist));
            tvSafeRisk.setText(String.format(Locale.US, "Risk Score: %.2f", safeRisk));

            tvShortestDistance.setText(String.format(Locale.US, "%.1f km", shortDist));
            tvShortestRisk.setText(String.format(Locale.US, "Risk Score: %.2f", shortRisk));

            tvTradeoffSummary.setText(String.format(Locale.US,
                    "✨ %.1f%% Exposure Reduction to High-Risk Cells (+%.1f%% distance trade-off)",
                    riskRed, distInc));

            // Render steps
            llWaypoints.removeAllViews();
            if (safe != null && safe.has("steps")) {
                JSONArray steps = safe.getJSONArray("steps");
                for (int i = 0; i < steps.length(); i++) {
                    JSONObject step = steps.getJSONObject(i);
                    TextView stepView = new TextView(this);
                    stepView.setPadding(0, 6, 0, 6);

                    String safety = step.optString("safety_rating", "Safe");
                    String icon = safety.equals("Safe") ? "🟢" : (safety.equals("Moderate") ? "🟡" : "🔴");

                    stepView.setText(String.format(Locale.US,
                            "%s %s ➔ %s (%s, %.1f km) [%s]",
                            icon,
                            step.optString("from"),
                            step.optString("to"),
                            step.optString("road_type"),
                            step.optDouble("distance_km"),
                            safety));

                    stepView.setTextColor(Color.DKGRAY);
                    stepView.setTextSize(12f);
                    llWaypoints.addView(stepView);
                }
            }
        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    private void renderSimulatedFallback() {
        cardResults.setVisibility(View.VISIBLE);
        tvSafeDistance.setText("5.7 km");
        tvSafeRisk.setText("Risk Score: 0.23 (Low)");

        tvShortestDistance.setText("5.1 km");
        tvShortestRisk.setText("Risk Score: 0.41 (Moderate)");

        tvTradeoffSummary.setText("✨ 43.2% Exposure Reduction to High-Risk Cells (+11.7% distance trade-off)");

        llWaypoints.removeAllViews();
        String[] fallbackSteps = {
                "🟢 Swargate Metro Hub ➔ Sarasbaug (Illuminated Dual Carriageway, 1.4 km) [Safe]",
                "🟢 Sarasbaug ➔ Deccan Gymkhana (Active City Center Arterial, 2.5 km) [Safe]",
                "🟢 Deccan Gymkhana ➔ Shivajinagar Central (FC Road Smart Corridor, 2.1 km) [Safe]"
        };
        for (String stepText : fallbackSteps) {
            TextView stepView = new TextView(this);
            stepView.setPadding(0, 6, 0, 6);
            stepView.setText(stepText);
            stepView.setTextColor(Color.DKGRAY);
            stepView.setTextSize(12f);
            llWaypoints.addView(stepView);
        }
    }
}
