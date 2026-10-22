package expo.modules.surakshaxnative

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/**
 * SOS countdown that runs natively, so it keeps ticking while the app is in the background
 * (React Native pauses JavaScript timers there). Shows a heads-up notification with an
 * "I'm safe" button; when it reaches zero the app is told to send the SOS.
 */
object SosCountdown {
  const val CHANNEL_ID = "surakshax_sos"
  private const val NOTIFICATION_ID = 4102
  const val ACTION_CANCEL = "expo.modules.surakshaxnative.SOS_CANCEL"

  private val handler = Handler(Looper.getMainLooper())
  private var remaining = 0
  private var reason = ""

  @Volatile
  var running = false
    private set

  /** Set by the module: (eventName, reason) */
  var listener: ((String, String) -> Unit)? = null

  fun start(context: Context, seconds: Int, why: String) {
    handler.removeCallbacksAndMessages(null)
    reason = why
    remaining = seconds
    running = true
    ProtectionService.ensureChannels(context)
    tick(context.applicationContext)
  }

  fun state(): Map<String, Any> = mapOf("running" to running, "remaining" to remaining, "reason" to reason)

  private fun tick(context: Context) {
    if (!running) return
    if (remaining <= 0) {
      running = false
      NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID)
      listener?.invoke("onSosCountdownFinished", reason)
      return
    }
    show(context)
    remaining -= 1
    handler.postDelayed({ tick(context) }, 1000)
  }

  /** Stops the countdown. fromUser = the "I'm safe" button or the app cancelled it. */
  fun cancel(context: Context, notify: Boolean = true) {
    if (!running) return
    running = false
    handler.removeCallbacksAndMessages(null)
    NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID)
    if (notify) listener?.invoke("onSosCountdownCancelled", reason)
  }

  private fun show(context: Context) {
    val cancelIntent = PendingIntent.getBroadcast(
      context,
      1,
      Intent(context, SosActionReceiver::class.java).setAction(ACTION_CANCEL),
      PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
    val notification = NotificationCompat.Builder(context, CHANNEL_ID)
      .setSmallIcon(R.drawable.surakshax_notification)
      .setContentTitle("SOS in $remaining s")
      .setContentText("Your contacts will be alerted. Tap I'm safe to cancel.")
      .setPriority(NotificationCompat.PRIORITY_MAX)
      .setCategory(NotificationCompat.CATEGORY_ALARM)
      .setOngoing(true)
      .setOnlyAlertOnce(false)
      .setVibrate(longArrayOf(0, 300))
      .setContentIntent(ProtectionService.openAppIntent(context))
      .addAction(0, "I'm safe", cancelIntent)
      .build()
    try {
      NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification)
    } catch (e: SecurityException) {
      // Notifications not allowed: the countdown still runs and the SOS is still sent
    }
  }
}

class SosActionReceiver : BroadcastReceiver() {
  override fun onReceive(context: Context, intent: Intent) {
    if (intent.action == SosCountdown.ACTION_CANCEL) SosCountdown.cancel(context)
  }
}
