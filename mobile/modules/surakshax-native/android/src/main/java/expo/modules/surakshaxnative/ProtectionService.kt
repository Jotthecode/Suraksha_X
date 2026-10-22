package expo.modules.surakshaxnative

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat

/**
 * Foreground service that keeps SurakshaX running while the user is in other apps or the screen
 * is off, so voice, motion and location SOS triggers keep working. Android only lets an app use the
 * microphone and location in the background while such a service (with a visible notification) runs.
 */
class ProtectionService : Service() {
  companion object {
    const val CHANNEL_ID = "surakshax_protection"
    const val NOTIFICATION_ID = 4101
    private const val EXTRA_TITLE = "title"
    private const val EXTRA_TEXT = "text"
    private const val EXTRA_MIC = "mic"
    private const val EXTRA_LOCATION = "location"

    @Volatile
    var isRunning = false
      private set

    fun start(context: Context, title: String, text: String, mic: Boolean, location: Boolean) {
      val intent = Intent(context, ProtectionService::class.java)
        .putExtra(EXTRA_TITLE, title)
        .putExtra(EXTRA_TEXT, text)
        .putExtra(EXTRA_MIC, mic)
        .putExtra(EXTRA_LOCATION, location)
      ContextCompat.startForegroundService(context, intent)
    }

    fun stop(context: Context) {
      context.stopService(Intent(context, ProtectionService::class.java))
    }

    fun ensureChannels(context: Context) {
      if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
      val manager = context.getSystemService(NotificationManager::class.java)
      manager.createNotificationChannel(
        NotificationChannel(CHANNEL_ID, "Protection", NotificationManager.IMPORTANCE_LOW).apply {
          description = "Shown while SurakshaX listens for SOS triggers"
          setShowBadge(false)
        }
      )
      manager.createNotificationChannel(
        NotificationChannel(SosCountdown.CHANNEL_ID, "SOS alerts", NotificationManager.IMPORTANCE_HIGH).apply {
          description = "SOS countdown and alerts"
          enableVibration(true)
        }
      )
    }

    fun openAppIntent(context: Context): PendingIntent? {
      val launch = context.packageManager.getLaunchIntentForPackage(context.packageName) ?: return null
      launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
      return PendingIntent.getActivity(
        context, 0, launch, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
      )
    }

    fun buildNotification(context: Context, title: String, text: String): Notification =
      NotificationCompat.Builder(context, CHANNEL_ID)
        .setSmallIcon(R.drawable.surakshax_notification)
        .setContentTitle(title)
        .setContentText(text)
        .setOngoing(true)
        .setOnlyAlertOnce(true)
        .setPriority(NotificationCompat.PRIORITY_LOW)
        .setCategory(NotificationCompat.CATEGORY_SERVICE)
        .setContentIntent(openAppIntent(context))
        .build()
  }

  private var wakeLock: PowerManager.WakeLock? = null

  override fun onBind(intent: Intent?): IBinder? = null

  private fun granted(permission: String) =
    ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    ensureChannels(this)
    val title = intent?.getStringExtra(EXTRA_TITLE) ?: "SurakshaX"
    val text = intent?.getStringExtra(EXTRA_TEXT) ?: "Protection is on"
    val wantMic = intent?.getBooleanExtra(EXTRA_MIC, false) ?: false
    val wantLocation = intent?.getBooleanExtra(EXTRA_LOCATION, true) ?: true
    val notification = buildNotification(this, title, text)

    // Only declare the service types whose permission is granted; Android 14 rejects the others
    var type = 0
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
      if (wantMic && granted(Manifest.permission.RECORD_AUDIO)) {
        type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
      }
      if (wantLocation && (granted(Manifest.permission.ACCESS_FINE_LOCATION) ||
          granted(Manifest.permission.ACCESS_COARSE_LOCATION))) {
        type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
      }
      if (type == 0 && Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
        // Motion-only protection (shake / running) has no dedicated type
        type = ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
      }
    }

    try {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && type != 0) {
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, type)
      } else {
        startForeground(NOTIFICATION_ID, notification)
      }
    } catch (e: Exception) {
      android.util.Log.w("SurakshaX", "Could not start protection service: ${e.message}")
      stopSelf()
      return START_NOT_STICKY
    }

    if (wakeLock == null) {
      // Keeps the CPU awake with the screen off so motion and speech events keep being processed
      wakeLock = (getSystemService(Context.POWER_SERVICE) as PowerManager)
        .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SurakshaX:protection")
        .apply { setReferenceCounted(false); acquire() }
    }
    isRunning = true
    // Not sticky: if Android kills the app, a restarted service without the app would only pretend to protect
    return START_NOT_STICKY
  }

  override fun onDestroy() {
    wakeLock?.let { if (it.isHeld) it.release() }
    wakeLock = null
    isRunning = false
    super.onDestroy()
  }
}
