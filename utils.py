import random
import string
import logging
import os
import base64
from datetime import datetime, timezone

import resend

from database import SessionLocal
import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Resend with your API key from environment variables
resend.api_key = os.getenv("RESEND_API_KEY")

# ─────────────────────────────────────────────
# Shared sender identity
# ─────────────────────────────────────────────
SENDER_EMAIL = "Hawkman Labs <no-reply@krossovertransport.com>"


def generate_otp(length: int = 6) -> str:
    secure_random = random.SystemRandom()
    return ''.join(secure_random.choice(string.digits) for _ in range(length))


def send_otp_email(email: str, otp_code: str):
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [email],
            "subject": "Your Hawkman Auth Verification Code",
            "html": f"<h2>Your code: {otp_code}</h2>",
            "text": f"Your verification code is: {otp_code}",
        }

        email_response = resend.Emails.send(params)
        logger.info(f"Successfully sent email to {email}. Message ID: {email_response.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email via Resend: {e}")
        return False


def send_lead_magnet_email(delivery_id: int, email: str, name: str, mapping: dict):
    """
    Background task to dispatch the Education Starter or Deeper pack PDF via Resend.
    Reads the PDF, attaches it (base64), sends the email, and updates the
    LeadDelivery row to SENT (or FAILED with error_message).
    """
    file_path = mapping["file_path"]
    subject = mapping["subject"]
    db = SessionLocal()

    try:
        delivery = db.query(models.LeadDelivery).filter(
            models.LeadDelivery.id == delivery_id
        ).first()

        if not delivery:
            logger.warning(f"[lead-magnet] Delivery {delivery_id} not found; skipping.")
            return

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Lead magnet file missing on disk: {file_path}")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        encoded_content = base64.b64encode(file_bytes).decode("utf-8")
        file_name = os.path.basename(file_path)
        pretty_pack_name = mapping["magnet"].replace("_", " ")

        params = {
            "from": SENDER_EMAIL,
            "to": [email],
            "subject": subject,
            "html": f"""
                <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                    <h2>Hi {name},</h2>
                    <p>Thanks for opting in! As requested, your
                       <b>{pretty_pack_name}</b> is attached to this email.</p>
                    <p>If you have any questions or want to dive deeper, feel free to reply directly.</p>
                    <br>
                    <p>Best regards,</p>
                    <p><b>Hawkman Team</b></p>
                </div>
            """,
            "text": (
                f"Hi {name},\n\n"
                f"Thanks for opting in! Your {pretty_pack_name} is attached.\n\n"
                f"— Hawkman Team"
            ),
            "attachments": [
                {
                    "filename": file_name,
                    "content": encoded_content,
                }
            ],
        }

        response = resend.Emails.send(params)
        logger.info(
            f"[lead-magnet] Sent {pretty_pack_name} to {email}. "
            f"Message ID: {response.get('id') if isinstance(response, dict) else response}"
        )

        delivery.delivery_status = "SENT"
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.error_message = None
        db.commit()

    except Exception as e:
        logger.error(f"[lead-magnet] Failed for {email}: {e}")
        db.rollback()
        # re-fetch in case rollback detached the object
        delivery = db.query(models.LeadDelivery).filter(
            models.LeadDelivery.id == delivery_id
        ).first()
        if delivery:
            delivery.delivery_status = "FAILED"
            delivery.error_message = str(e)[:500]
            try:
                db.commit()
            except Exception as commit_err:
                db.rollback()
                logger.error(f"[lead-magnet] Could not record FAILED status: {commit_err}")
    finally:
        db.close()