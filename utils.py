import random
import string
import logging

# Set up a basic logger so our "emails" look nice in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    Simulates sending an email. In a real app, this is where you would connect 
    to an SMTP server or an API like Resend, Mailgun, or AWS SES.
    """
    # ---------------------------------------------------------
    # TODO FOR V3: Replace this block with actual SMTP logic
    # ---------------------------------------------------------
    
    # We print a highly visible block to the terminal so you can copy the OTP easily
    print("\n" + "="*50)
    print(f"📧 EMAIL SENT TO: {email}")
    print(f"🔐 YOUR SECURE OTP CODE IS: {otp_code}")
    print("="*50 + "\n")
    
    # We also log it just to be thorough
    logger.info(f"Simulated email sent to {email} with OTP.")
    
    return True