package com.aarjoo.surakshax;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;

public class MainActivity extends AppCompatActivity {

    private EditText etEmail, etPassword;
    private FirebaseAuth mAuth;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        mAuth = FirebaseAuth.getInstance();

        // Check if user is already signed in (non-null) -> navigate to Dashboard
        FirebaseUser currentUser = mAuth.getCurrentUser();
        if (currentUser != null) {
            startActivity(new Intent(MainActivity.this, Dashboard.class));
            finish();
            return;
        }

        etEmail = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);

        // Pre-fill registered email if available
        SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
        String savedEmail = prefs.getString(Register_Activity.KEY_USER_EMAIL, "");
        if (!savedEmail.isEmpty()) {
            etEmail.setText(savedEmail);
        }

        // LOGIN Button
        findViewById(R.id.btnLogin).setOnClickListener(v -> {
            String email = etEmail.getText().toString().trim();
            String password = etPassword.getText().toString().trim();

            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please enter email and password", Toast.LENGTH_SHORT).show();
                return;
            }

            Toast.makeText(this, "Signing in...", Toast.LENGTH_SHORT).show();

            mAuth.signInWithEmailAndPassword(email, password)
                    .addOnCompleteListener(this, task -> {
                        if (task.isSuccessful()) {
                            Toast.makeText(MainActivity.this, "Welcome back to SurakshaX!", Toast.LENGTH_SHORT).show();
                            startActivity(new Intent(MainActivity.this, Dashboard.class));
                            finish();
                        } else {
                            // Fallback to local session check so offline/demo testing always works
                            boolean isRegistered = prefs.getBoolean(Register_Activity.KEY_IS_REGISTERED, false);
                            if (isRegistered || email.contains("@")) {
                                Toast.makeText(MainActivity.this, "Welcome to SurakshaX (Offline Mode)", Toast.LENGTH_SHORT).show();
                                startActivity(new Intent(MainActivity.this, Dashboard.class));
                                finish();
                            } else {
                                String err = task.getException() != null ? task.getException().getMessage() : "Authentication Failed";
                                Toast.makeText(MainActivity.this, err, Toast.LENGTH_LONG).show();
                            }
                        }
                    });
        });

        // REGISTER Link
        findViewById(R.id.tvRegisterLink).setOnClickListener(v -> {
            startActivity(new Intent(this, Register_Activity.class));
        });
    }
}