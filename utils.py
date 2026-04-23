import random
import string
import logging
import os
import resend

# Set up a basic logger so our "emails" look nice in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the key from your .env file
# If it's not there, this just returns None and our feature flag catches it
resend.api_key = os.getenv("RESEND_API_KEY")

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
    Sends an email using Resend. If no API key is found in the environment,
    it safely falls back to simulating the email in the terminal.
    """
    # =========================================================
    # FEATURE FLAG: The Safety Net
    # =========================================================
    if not resend.api_key:
        print("\n" + "="*50)
        print(f"📧 SIMULATED EMAIL TO: {email}")
        print(f"🔐 YOUR SECURE OTP CODE IS: {otp_code}")
        print("="*50 + "\n")
        
        logger.info(f"Simulated email sent to {email} with OTP.")
        return True

    # =========================================================
    # THE REAL DEAL: Resend API Sandbox
    # =========================================================
    try:
        # NOTE: Because we are in Sandbox mode, 'from' must be Acme <onboarding@resend.dev>
        # and 'to' MUST be the exact email address you used to sign up for Resend!
        params = {
            "from": "Hawkman Labs <onboarding@resend.dev>", 
            "to": [email], 
            "subject": "Your Talent Oasis Verification Code",
            "html": f"<h2>Welcome to Talent Oasis!</h2><p>Your 6-digit verification code is: <strong style='font-size: 24px; letter-spacing: 2px;'>{otp_code}</strong></p><p>This code expires in 10 minutes.</p>",
        }

        response = resend.Emails.send(params)
        
        print("\n" + "="*50)
        print(f"✅ REAL API EMAIL SENT TO {email}")
        print(f"🆔 Resend ID: {response['id']}")
        print("="*50 + "\n")
        
        logger.info(f"Real email sent via Resend to {email}.")
        return True
        
    except Exception as e:
        print("\n" + "❌"*25)
        print(f"ERROR SENDING RESEND EMAIL: {e}")
        print("❌"*25 + "\n")
        
        logger.error(f"Failed to send real email to {email}: {e}")
        return False