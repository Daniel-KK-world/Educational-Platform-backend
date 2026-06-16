import random
import string
import logging
import os
import resend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Resend with your API key from environment variables
resend.api_key = os.getenv("RESEND_API_KEY")

def generate_otp(length: int = 6) -> str:
    secure_random = random.SystemRandom()
    return ''.join(secure_random.choice(string.digits) for _ in range(length))

def send_otp_email(email: str, otp_code: str):
    try:
        # Define the email parameters using your verified domain
        params = {
            "from": "Hawkman Labs <no-reply@kensvic.com>",
            "to": [email],
            "subject": "Your Hawkman Auth Verification Code",
            "html": f"<h2>Your code: {otp_code}</h2>",
            "text": f"Your verification code is: {otp_code}"
        }

        # Send the email via Resend API
        email_response = resend.Emails.send(params)
        
        logger.info(f"Successfully sent email to {email}. Message ID: {email_response.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email via Resend: {e}")
        return False