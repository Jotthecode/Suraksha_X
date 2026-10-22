package com.aarjoo.surakshax;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;

public class Profile extends AppCompatActivity {

    private EditText etProfileName;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_profile);

        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        toolbar.setNavigationOnClickListener(v -> onBackPressed());

        etProfileName = findViewById(R.id.etProfileName);

        // Load saved profile name
        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        String savedName = prefs.getString(Register_Activity.KEY_USER_NAME, "Aarjoo Dahiya");
        etProfileName.setText(savedName);

        findViewById(R.id.btnEditContacts).setOnClickListener(v -> startActivity(new Intent(this, Contacts.class)));
        findViewById(R.id.btnSettings).setOnClickListener(v -> startActivity(new Intent(this, Permission.class)));

        // Save updated name
        findViewById(R.id.btnSave).setOnClickListener(v -> {
            String updatedName = etProfileName.getText().toString().trim();
            if (!updatedName.isEmpty()) {
                prefs.edit().putString(Register_Activity.KEY_USER_NAME, updatedName).apply();
                Toast.makeText(this, "Profile updated successfully!", Toast.LENGTH_SHORT).show();
            }
            finish();
        });
    }
}