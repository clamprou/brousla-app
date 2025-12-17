"""Email service for sending confirmation emails via Resend."""
import resend
from app.config import settings
from typing import Optional


def send_confirmation_email(email: str, token: str, confirmation_url: str) -> None:
    """
    Send email confirmation email via Resend.
    
    Args:
        email: Recipient email address
        token: Email verification token
        confirmation_url: Full URL to confirmation page with token
    """
    try:
        # Set API key for Resend
        resend.api_key = settings.resend_api_key
        
        subject = "Confirm Your Email Address - Brousla App"
        
        # HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirm Your Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #1f2937; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: #ffffff; margin: 0;">Brousla App</h1>
            </div>
            <div style="background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #111827; margin-top: 0;">Confirm Your Email Address</h2>
                <p style="color: #4b5563;">Thank you for registering with Brousla App! Please confirm your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirmation_url}" 
                       style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Confirm Email Address
                    </a>
                </div>
                <p style="color: #4b5563; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #2563eb; font-size: 12px; word-break: break-all; background-color: #e5e7eb; padding: 10px; border-radius: 4px;">
                    {confirmation_url}
                </p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
                    This confirmation link will expire in 24 hours. If you didn't create an account with Brousla App, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Confirm Your Email Address - Brousla App
        
        Thank you for registering with Brousla App! Please confirm your email address by visiting the following link:
        
        {confirmation_url}
        
        This confirmation link will expire in 24 hours. If you didn't create an account with Brousla App, please ignore this email.
        """
        
        # Send email via Resend
        params = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
        
        # Use the emails module from resend
        from resend.emails._emails import Emails
        emails = Emails()
        response = emails.send(params)
        
        # Resend returns a dict with 'id' on success, or raises an exception on error
        if not response or 'id' not in response:
            raise Exception("Resend API returned an invalid response")
            
    except Exception as e:
        # Log error but don't expose Resend details to user
        print(f"Error sending confirmation email: {e}")
        raise Exception("Failed to send confirmation email. Please try again later.")


