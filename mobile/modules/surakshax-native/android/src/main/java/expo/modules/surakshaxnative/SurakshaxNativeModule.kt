package expo.modules.surakshaxnative

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.telecom.TelecomManager
import android.telephony.SmsManager
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.os.bundleOf
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * Sends emergency SMS directly from the device SIM, places calls, and runs background protection
 * (foreground service + native SOS countdown), so SOS alerts go out without the user tapping
 * Send or Call, even while the app is in the background.
 */
class SurakshaxNativeModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  private fun hasPermission(permission: String) =
    ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

  @Suppress("DEPRECATION")
  private fun smsManager(): SmsManager =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      context.getSystemService(SmsManager::class.java)
    } else {
      SmsManager.getDefault()
    }

  override fun definition() = ModuleDefinition {
    Name("SurakshaxNative")

    Events("onSosCountdownFinished", "onSosCountdownCancelled")

    OnCreate {
      SosCountdown.listener = { name, reason -> sendEvent(name, bundleOf("reason" to reason)) }
    }

    OnDestroy {
      SosCountdown.listener = null
    }

    Function("canSendSms") {
      context.packageManager.hasSystemFeature(PackageManager.FEATURE_TELEPHONY) &&
        hasPermission(Manifest.permission.SEND_SMS)
    }

    // Returns a list of {phone, status, error?} results, one per recipient.
    AsyncFunction("sendSmsAsync") { phones: List<String>, message: String ->
      if (!hasPermission(Manifest.permission.SEND_SMS)) {
        return@AsyncFunction phones.map { mapOf("phone" to it, "status" to "no_permission") }
      }
      val manager = smsManager()
      phones.map { phone ->
        try {
          val parts = manager.divideMessage(message)
          if (parts.size > 1) {
            manager.sendMultipartTextMessage(phone, null, parts, null, null)
          } else {
            manager.sendTextMessage(phone, null, message, null, null)
          }
          mapOf("phone" to phone, "status" to "sent")
        } catch (e: Exception) {
          mapOf("phone" to phone, "status" to "failed", "error" to (e.message ?: e.javaClass.simpleName))
        }
      }
    }

    // Places a call directly when CALL_PHONE is granted, otherwise opens the dialer.
    AsyncFunction("callAsync") { phone: String ->
      val direct = hasPermission(Manifest.permission.CALL_PHONE)
      val intent = Intent(if (direct) Intent.ACTION_CALL else Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
      intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
      context.startActivity(intent)
      if (direct) "calling" else "dialer_opened"
    }

    // Starts a call without any tap, also from the background (TelecomManager is not an activity start).
    AsyncFunction("placeCallAsync") { phone: String ->
      if (!hasPermission(Manifest.permission.CALL_PHONE)) return@AsyncFunction "no_permission"
      try {
        val telecom = context.getSystemService(Context.TELECOM_SERVICE) as TelecomManager
        telecom.placeCall(Uri.fromParts("tel", phone, null), Bundle())
        "calling"
      } catch (e: Exception) {
        "failed: ${e.message ?: e.javaClass.simpleName}"
      }
    }

    // What the app is allowed to do right now (for the in-app permission check).
    Function("permissionStatus") {
      val power = context.getSystemService(Context.POWER_SERVICE) as PowerManager
      mapOf(
        "sms" to hasPermission(Manifest.permission.SEND_SMS),
        "call" to hasPermission(Manifest.permission.CALL_PHONE),
        "microphone" to hasPermission(Manifest.permission.RECORD_AUDIO),
        "location" to (hasPermission(Manifest.permission.ACCESS_FINE_LOCATION) ||
          hasPermission(Manifest.permission.ACCESS_COARSE_LOCATION)),
        "notifications" to NotificationManagerCompat.from(context).areNotificationsEnabled(),
        "batteryUnrestricted" to power.isIgnoringBatteryOptimizations(context.packageName),
        "hasTelephony" to context.packageManager.hasSystemFeature(PackageManager.FEATURE_TELEPHONY),
        "sdk" to Build.VERSION.SDK_INT,
        "manufacturer" to Build.MANUFACTURER
      )
    }

    // App info page: Permissions, and on Android 13+ the "⋮ > Allow restricted settings" menu.
    Function("openAppSettings") {
      val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", context.packageName, null))
      intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
      context.startActivity(intent)
    }

    // Battery optimisation list, so the user can set SurakshaX to "Unrestricted".
    Function("openBatterySettings") {
      val intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
      intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
      try {
        context.startActivity(intent)
      } catch (e: Exception) {
        val fallback = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", context.packageName, null))
        fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(fallback)
      }
    }

    Function("startProtection") { title: String, text: String, mic: Boolean, location: Boolean ->
      ProtectionService.start(context, title, text, mic, location)
      true
    }

    Function("stopProtection") {
      ProtectionService.stop(context)
    }

    Function("isProtectionRunning") {
      ProtectionService.isRunning
    }

    Function("startSosCountdown") { seconds: Int, reason: String ->
      SosCountdown.start(context, seconds, reason)
    }

    // Cancels without reporting it as the user's "I'm safe" (used when the app takes over the countdown).
    Function("cancelSosCountdown") { notify: Boolean ->
      SosCountdown.cancel(context, notify)
    }

    Function("getSosCountdown") {
      SosCountdown.state()
    }
  }
}
