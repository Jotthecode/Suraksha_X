package expo.modules.surakshaxnative

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * Sends emergency SMS directly from the device SIM and places direct phone calls,
 * so SOS alerts reach guardians even when no cloud SMS gateway (Twilio) is configured.
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
  }
}
