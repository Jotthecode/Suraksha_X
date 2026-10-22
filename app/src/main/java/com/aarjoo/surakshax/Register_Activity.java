package com.aarjoo.surakshax;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.HashMap;
import java.util.Map;

public class Register_Activity extends AppCompatActivity {

    public static final String KEY_USER_NAME = "user_full_name";
    public static final String KEY_USER_EMAIL = "user_email";
    public static final String KEY_USER_GENDER = "user_gender";
    public static final String KEY_IS_REGISTERED = "is_user_registered";

    private FirebaseAuth mAuth;
    private FirebaseFirestore db;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_register);

        mAuth = FirebaseAuth.getInstance();
        db = FirebaseFirestore.getInstance();

        EditText etFullName = findViewById(R.id.etFullName);
        EditText etEmail = findViewById(R.id.etEmail);
        EditText etPassword = findViewById(R.id.etPassword);
        RadioGroup rgGender = findViewById(R.id.rgGender);

        findViewById(R.id.btnContinue).setOnClickListener(v -> {
            String name = etFullName.getText().toString().trim();
            String email = etEmail.getText().toString().trim();
            String password = etPassword.getText().toString().trim();

            if (name.isEmpty() || email.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please fill in all registration fields", Toast.LENGTH_SHORT).show();
                return;
            }

            if (password.length() < 6) {
                Toast.makeText(this, "Password must be at least 6 characters", Toast.LENGTH_SHORT).show();
                return;
            }

            int selectedGenderId = rgGender.getCheckedRadioButtonId();
            RadioButton selectedGenderBtn = findViewById(selectedGenderId);
            String gender = selectedGenderBtn != null ? selectedGenderBtn.getText().toString() : "Female";

            // Save to persistent SharedPreferences immediately (offline resilience)
            SharedPreferences prefs = getSharedPreferences(Contacts.PREFS_NAME, MODE_PRIVATE);
            prefs.edit()
                    .putString(KEY_USER_NAME, name)
                    .putString(KEY_USER_EMAIL, email)
                    .putString(KEY_USER_GENDER, gender)
                    .putBoolean(KEY_IS_REGISTERED, true)
                    .apply();

            Toast.makeText(this, "Creating Firebase account...", Toast.LENGTH_SHORT).show();

            // Firebase Authentication
            mAuth.createUserWithEmailAndPassword(email, password)
                    .addOnCompleteListener(this, task -> {
                        if (task.isSuccessful()) {
                            FirebaseUser user = mAuth.getCurrentUser();
                            if (user != null) {
                                // Save profile to Cloud Firestore
                                Map<String, Object> userData = new HashMap<>();
                                userData.put("name", name);
                                userData.put("email", email);
                                userData.put("gender", gender);
                                userData.put("created_at", System.currentTimeMillis());

                                db.collection("users").document(user.getUid())
                                        .set(userData);
                            }
                            Toast.makeText(Register_Activity.this, "Firebase Account Created!", Toast.LENGTH_SHORT).show();
                        } else {
                            String err = task.getException() != null ? task.getException().getMessage() : "Auth notice";
                            Toast.makeText(Register_Activity.this, "Notice: " + err, Toast.LENGTH_SHORT).show();
                        }

                        // Always proceed to Contacts setup
                        startActivity(new Intent(Register_Activity.this, Contacts.class));
                        finish();
                    });
        });
    }
}