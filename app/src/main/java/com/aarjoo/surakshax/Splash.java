package com.aarjoo.surakshax;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.view.animation.AlphaAnimation;
import android.widget.ImageView;
import androidx.appcompat.app.AppCompatActivity;

public class Splash extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        // Yahan ID check karein (XML wali honi chahiye)
        ImageView logo = findViewById(R.id.splashLogo);

        AlphaAnimation fadeIn = new AlphaAnimation(0.0f, 1.0f);
        fadeIn.setDuration(1500);

        if (logo != null) {
            logo.startAnimation(fadeIn);
        }

        new Handler().postDelayed(() -> {
            startActivity(new Intent(Splash.this, MainActivity.class));
            finish();
        }, 3000);
    }
}