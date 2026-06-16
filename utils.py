import random
import string
import logging
import os
import smtplib
from email.message import EmailMessage

# Set up a basic logger so our "emails" look nice in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the credentials from your .env file
# If they aren't there, our feature flag catches it
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

def generate_otp(length: int = 6) -> str:
    """
    Generates a cryptographically secure random N-digit string.
    We use SystemRandom instead of the standard random for bank-grade security.
    """
    # string.digits is just '0123456789'
    secure_random = random.SystemRandom()
    otp = ''.join(secure_random.choice(string.digits) for _ in range(length))
    return otp

def send_otp_email(email: str, otp_code: str):
    """
    Sends an email using standard SMTP. If no SMTP credentials are found in the environment,
    it safely falls back to simulating the email in the terminal.
    """
    # =========================================================
    # FEATURE FLAG: The Safety Net
    # =========================================================
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        print("\n" + "="*50)
        print(f"📧 SIMULATED EMAIL TO: {email}")
        print(f"🔐 YOUR SECURE OTP CODE IS: {otp_code}")
        print("⚠️  (No SMTP credentials found in .env, running in simulation mode)")
        print("="*50 + "\n")
        
        logger.info(f"Simulated email sent to {email} with OTP.")
        return True

    # =========================================================
    # THE REAL DEAL: Gmail SMTP Integration
    # =========================================================
    try:
        # Build the email
        msg = EmailMessage()
        msg['Subject'] = "Your Hawkman Auth Verification Code"
        msg['From'] = f"Hawkman Labs <{SMTP_EMAIL}>"
        msg['To'] = email
        
        # Keeping your HTML styling!
        msg.add_alternative(f"""
        <h2>Welcome!</h2>
        <p>Your 6-digit verification code is: <strong style='font-size: 24px; letter-spacing: 2px;'>{otp_code}</strong></p>
        <p>This code expires in 10 minutes.</p>
        """, subtype='html')

        # Connect to Gmail's SMTP server
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.send_message(msg)
        
        print("\n" + "="*50)
        print(f"✅ REAL EMAIL SENT TO {email} VIA SMTP")
        print("="*50 + "\n")
        
        logger.info(f"Real email sent via SMTP to {email}.")
        return True
        
    except Exception as e:
        print("\n" + "❌"*25)
        print(f"ERROR SENDING SMTP EMAIL: {e}")
        print("❌"*25 + "\n")
        
        logger.error(f"Failed to send real email to {email}: {e}")
        return False