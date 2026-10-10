"""
SafeHer Notification Service
------------------------------
Default: MockNotifier — logs to console, no external API needed.
Email/SMS: Optional, activated only when .env credentials are set.
Never hard-codes credentials.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod

from backend.config import settings
from backend.models.contact import EmergencyContact
from backend.models.emergency import EmergencyEvent
from backend.models.notification import NotificationChannel

logger = logging.getLogger("safeher.notifications")


# ── Alert message builder ─────────────────────────────────────────────────────

def build_alert_message(event: EmergencyEvent, user_name: str, include_location: bool) -> str:
    lines = [
        f"⚠️ SafeHer Safety Alert",
        f"",
        f"{user_name} has triggered a safety alert.",
        f"Event type: {event.event_type.value.replace('_', ' ').title()}",
        f"Time: {event.created_at.strftime('%d %b %Y, %I:%M %p UTC')}",
    ]
    if include_location and event.location_link:
        lines.append(f"Last known location: {event.location_link}")
    if event.notes:
        lines.append(f"Note: {event.notes}")
    lines += [
        f"",
        f"Please check on them immediately.",
        f"— SafeHer Safety Platform",
    ]
    return "\n".join(lines)


# ── Notifier base ─────────────────────────────────────────────────────────────

class BaseNotifier(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> tuple[bool, str | None]:
        pass

    @abstractmethod
    def send_sms(self, to: str, body: str) -> tuple[bool, str | None]:
        pass


# ── Mock Notifier (default) ───────────────────────────────────────────────────

class MockNotifier(BaseNotifier):
    """
    Used during development. Prints alerts to console.
    No external API or credentials required.
    """
    def send_email(self, to: str, subject: str, body: str) -> tuple[bool, str | None]:
        logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject}\n{body}")
        return True, None

    def send_sms(self, to: str, body: str) -> tuple[bool, str | None]:
        logger.info(f"[MOCK SMS] To: {to}\n{body}")
        return True, None


# ── Email Notifier ────────────────────────────────────────────────────────────

class EmailNotifier(BaseNotifier):
    def send_email(self, to: str, subject: str, body: str) -> tuple[bool, str | None]:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to, msg.as_string())
            return True, None
        except Exception as e:
            return False, str(e)

    def send_sms(self, to: str, body: str) -> tuple[bool, str | None]:
        return False, "SMS not configured with EmailNotifier"


# ── Notifier factory ──────────────────────────────────────────────────────────

def get_notifier() -> BaseNotifier:
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        return EmailNotifier()
    return MockNotifier()


# ── Dispatch function ─────────────────────────────────────────────────────────

def dispatch_alert(
    event: EmergencyEvent,
    contacts: list[EmergencyContact],
    user_name: str,
    include_location: bool,
) -> list[dict]:
    """
    Sends alert to all active contacts.
    Returns list of notification result dicts for logging.
    """
    notifier = get_notifier()
    body = build_alert_message(event, user_name, include_location)
    subject = f"⚠️ SafeHer Alert — {user_name} needs attention"
    results = []

    for contact in contacts:
        if contact.email:
            success, error = notifier.send_email(contact.email, subject, body)
            results.append({
                "contact_id": contact.id,
                "channel": NotificationChannel.EMAIL if not isinstance(notifier, MockNotifier) else NotificationChannel.MOCK,
                "recipient": contact.email,
                "success": success,
                "error_message": error,
            })

        if contact.phone:
            success, error = notifier.send_sms(contact.phone, body)
            results.append({
                "contact_id": contact.id,
                "channel": NotificationChannel.SMS if not isinstance(notifier, MockNotifier) else NotificationChannel.MOCK,
                "recipient": contact.phone,
                "success": success,
                "error_message": error,
            })

    return results
