package com.aarjoo.surakshax;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;

public class Happy_Screen extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_safe_status);

        // 1. Toolbar Back Arrow Setup
        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setDisplayHomeAsUpEnabled(true);
        }

        // Back arrow click hone par Dashboard par bhejo
        toolbar.setNavigationOnClickListener(v -> goToDashboard());

        // 2. Button Click Setup (Check ID here)
        findViewById(R.id.btnBackHome).setOnClickListener(v -> {
            goToDashboard();
        });
    }

    // Ek common method Dashboard par jane ke liye
    private void goToDashboard() {
        Intent intent = new Intent(this, Dashboard.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        startActivity(intent);
        finish();
    }

    @Override
    public boolean onSupportNavigateUp() {
        goToDashboard();
        return true;
    }
}