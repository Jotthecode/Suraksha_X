"""Server-side SOS delivery through Twilio (optional; the app also texts from the phone's own SIM)."""

import logging
from xml.sax.saxutils import escape

from .. import config

log = logging.getLogger("surakshax.notify")


def normalize_phone_e164(phone: str, default_country_code: str = "+91") -> str:
    """'98765 43210' / '09876543210' -> '+919876543210'."""
    raw = "".join(ch for ch in str(phone or "") if ch.isdigit() or ch == "+")
    if not raw:
        return ""
    if raw.startswith("+"):
        return raw
    if raw.startswith("00"):
        return "+" + raw[2:]
    digits = raw.lstrip("0")
    if len(digits) == 10:
        return default_country_code + digits
    return "+" + digits


def send_sos(user_name: str, lat: float, lon: float, tracking_url: str, contacts: list, nearest: dict | None):
    """Texts every contact and calls the first one. Returns (sms_status, call_status)."""
    if not config.TWILIO_ENABLED:
        sms = [{"phone": c["phone"], "status": "not_sent_twilio_not_configured"} for c in contacts]
        return sms, ({"status": "not_initiated_twilio_not_configured"} if contacts else None)

    from twilio.rest import Client

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    body = (
        f"SOS from {user_name}. Location: https://maps.google.com/?q={lat:.6f},{lon:.6f} "
        f"Live tracking: {tracking_url}"
        + (f" Nearest police: {nearest['name']} ({nearest.get('phone') or '112'})" if nearest else " Call 112.")
        + " - SurakshaX"
    )

    sms_status = []
    for contact in contacts:
        phone = normalize_phone_e164(contact.get("phone", ""))
        if not phone:
            continue
        try:
            msg = client.messages.create(body=body, from_=config.TWILIO_PHONE_NUMBER, to=phone)
            sms_status.append({"phone": phone, "sid": msg.sid, "status": "sent"})
        except Exception as e:  # one bad number must not stop the others
            log.warning("Twilio SMS to %s failed: %s", phone, e)
            sms_status.append({"phone": phone, "status": "failed", "error": str(e)})

    call_status = None
    primary = normalize_phone_e164(contacts[0].get("phone", "")) if contacts else ""
    if primary:
        twiml = (
            "<Response><Say>Emergency. {} has sent an S O S alert from SurakshaX. "
            "Check your text messages for the live location.</Say></Response>"
        ).format(escape(user_name))
        try:
            call = client.calls.create(twiml=twiml, to=primary, from_=config.TWILIO_PHONE_NUMBER)
            call_status = {"phone": primary, "sid": call.sid, "status": "initiated"}
        except Exception as e:
            log.warning("Twilio call to %s failed: %s", primary, e)
            call_status = {"phone": primary, "status": "failed", "error": str(e)}
    return sms_status, call_status
