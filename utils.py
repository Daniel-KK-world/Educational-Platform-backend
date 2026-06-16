import random
import string
import logging
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.message import EmailMessage
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_otp(length: int = 6) -> str:
    secure_random = random.SystemRandom()
    return ''.join(secure_random.choice(string.digits) for _ in range(length))

def send_otp_email(email: str, otp_code: str):
    try:
        # Load your 3 keys from Environment Variables
        creds = Credentials(
            None,
            refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GMAIL_CLIENT_ID"),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        )

        # Build the Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Create the email
        msg = EmailMessage()
        msg['Subject'] = "Your Hawkman Auth Verification Code"
        msg['From'] = "Hawkman Labs <danielpossiblekwabi@gmail.com>"
        msg['To'] = email
        msg.set_content(f"Your verification code is: {otp_code}")
        msg.add_alternative(f"<h2>Your code: {otp_code}</h2>", subtype='html')

        # Encode and send
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()

        logger.info(f"Successfully sent email to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False