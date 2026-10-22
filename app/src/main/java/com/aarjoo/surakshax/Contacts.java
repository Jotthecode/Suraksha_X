package com.aarjoo.surakshax;

import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.HashMap;
import java.util.Map;

public class Contacts extends AppCompatActivity {

    public static final String PREFS_NAME = "SurakshaX_Prefs";
    public static final String KEY_GUARDIAN_NAME = "guardian_name_1";
    public static final String KEY_GUARDIAN_PHONE = "guardian_phone_1";
    public static final String KEY_GUARDIAN_PHONE_2 = "guardian_phone_2";

    private EditText etGuardianName1;
    private EditText etGuardianPhone1;
    private EditText etGuardianPhone2;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_contacts);

        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }

        etGuardianName1 = findViewById(R.id.etGuardianName1);
        etGuardianPhone1 = findViewById(R.id.etGuardianPhone1);
        etGuardianPhone2 = findViewById(R.id.etGuardianPhone2);
        ImageButton btnQuickCall = findViewById(R.id.btnQuickCall);

        // Load existing saved contacts from local preferences
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedName = prefs.getString(KEY_GUARDIAN_NAME, "");
        String savedPhone = prefs.getString(KEY_GUARDIAN_PHONE, "9302414220");
        String savedPhone2 = prefs.getString(KEY_GUARDIAN_PHONE_2, "");

        etGuardianName1.setText(savedName);
        etGuardianPhone1.setText(savedPhone);
        etGuardianPhone2.setText(savedPhone2);

        // Quick Call Button
        btnQuickCall.setOnClickListener(v -> {
            String phone = etGuardianPhone1.getText().toString().trim();
            if (!phone.isEmpty()) {
                Intent intent = new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + phone));
                startActivity(intent);
            } else {
                Toast.makeText(this, "Please enter a guardian phone number first", Toast.LENGTH_SHORT).show();
            }
        });

        // Save Contacts
        findViewById(R.id.btnSaveContacts).setOnClickListener(v -> {
            String name1 = etGuardianName1.getText().toString().trim();
            String phone1 = etGuardianPhone1.getText().toString().trim();
            String phone2 = etGuardianPhone2.getText().toString().trim();

            if (phone1.isEmpty()) {
                Toast.makeText(this, "Please enter Primary Guardian Phone Number", Toast.LENGTH_SHORT).show();
                return;
            }

            // 1. Save locally for instant offline availability
            SharedPreferences.Editor editor = prefs.edit();
            editor.putString(KEY_GUARDIAN_NAME, name1);
            editor.putString(KEY_GUARDIAN_PHONE, phone1);
            editor.putString(KEY_GUARDIAN_PHONE_2, phone2);
            editor.apply();

            // 2. Sync to Cloud Firestore if logged in
            FirebaseUser user = FirebaseAuth.getInstance().getCurrentUser();
            if (user != null) {
                Map<String, Object> contactData = new HashMap<>();
                contactData.put("guardian_name_1", name1);
                contactData.put("guardian_phone_1", phone1);
                contactData.put("guardian_phone_2", phone2);
                contactData.put("updated_at", System.currentTimeMillis());

                FirebaseFirestore.getInstance()
                        .collection("users")
                        .document(user.getUid())
                        .collection("contacts")
                        .document("emergency")
                        .set(contactData);
            }

            Toast.makeText(this, "Guardian Contacts Saved Successfully!", Toast.LENGTH_SHORT).show();

            // Proceed to Permission screen
            startActivity(new Intent(this, Permission.class));
            finish();
        });
    }

    @Override
    public boolean onSupportNavigateUp() {
        onBackPressed();
        return true;
    }
}