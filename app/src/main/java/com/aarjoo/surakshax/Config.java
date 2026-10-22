package com.aarjoo.surakshax;

import android.content.Context;
import android.content.SharedPreferences;

public class Config {

    // Default to local Android emulator mapping (10.0.2.2 accesses host machine localhost)
    // and provide cloud fallback
    public static final String DEFAULT_HOST = "http://10.0.2.2:5000";
    public static final String CLOUD_HOST = "https://surakshax-wa0i.onrender.com";

    private static final String PREF_SERVER_URL = "server_base_url";

    public static String getBaseUrl(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(Contacts.PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(PREF_SERVER_URL, DEFAULT_HOST);
    }

    public static void setBaseUrl(Context context, String url) {
        SharedPreferences prefs = context.getSharedPreferences(Contacts.PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString(PREF_SERVER_URL, url.trim()).apply();
    }

    public static String getAnalyzeUrl(Context context) {
        return getBaseUrl(context) + "/analyze_status";
    }

    public static String getPredictRiskUrl(Context context) {
        return getBaseUrl(context) + "/predict_risk";
    }

    public static String getSafeRouteUrl(Context context) {
        return getBaseUrl(context) + "/safe_route";
    }

    public static String getVoiceSosUrl(Context context) {
        return getBaseUrl(context) + "/voice_sos";
    }

    public static String getNearestPoliceUrl(Context context) {
        return getBaseUrl(context) + "/police/nearest";
    }

    public static String getEmergencyDispatchUrl(Context context) {
        return getBaseUrl(context) + "/emergency_dispatch";
    }

    public static String getTrackingUpdateUrl(Context context) {
        return getBaseUrl(context) + "/tracking/update";
    }

    public static String getLiveTrackWebUrl(Context context, String sessionId) {
        return getBaseUrl(context) + "/track/" + sessionId;
    }
}
