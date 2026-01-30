"""
Email utility functions for sending confirmation emails.
Supports SMTP configuration via environment variables.
"""

import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone


def get_smtp_config():
    """
    Get SMTP configuration from environment variables.
    Returns dict with host, port, user, pass, from_addr.
    Returns None if SMTP is not configured (development mode).
    """
    host = os.environ.get("SMTP_HOST", "").strip()
    port = os.environ.get("SMTP_PORT", "587").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    from_addr = os.environ.get("MAIL_FROM", "").strip()
    
    if not host or not user or not password or not from_addr:
        return None  # SMTP not configured
    
    try:
        port = int(port)
    except ValueError:
        port = 587
    
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr
    }


def generate_confirmation_token():
    """
    Generate a secure, unguessable confirmation token.
    Returns a URL-safe 32-character hex string.
    """
    return secrets.token_urlsafe(32)


def is_token_expired(sent_at_iso: str, hours=24):
    """
    Check if a confirmation token has expired.
    
    Args:
        sent_at_iso: ISO format timestamp when token was sent
        hours: expiration time in hours (default 24)
    
    Returns:
        True if token is expired, False otherwise
    """
    if not sent_at_iso:
        return True
    
    try:
        sent_at = datetime.fromisoformat(sent_at_iso.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        expiration = sent_at + timedelta(hours=hours)
        return now > expiration
    except Exception:
        return True


def send_confirmation_email(to_email: str, confirmation_url: str):
    """
    Send email confirmation with a secure token link.
    
    Args:
        to_email: recipient email address
        confirmation_url: full URL to confirm the account
    
    Returns:
        True if email sent successfully, False otherwise
    
    In development mode (no SMTP config), prints the link to console.
    """
    smtp_config = get_smtp_config()
    
    # Development mode: print to console
    if not smtp_config:
        print("=" * 70)
        print("📧 EMAIL CONFIRMATION (DEVELOPMENT MODE)")
        print("=" * 70)
        print(f"To: {to_email}")
        print(f"Subject: Confirma tu cuenta - Gastos App")
        print()
        print("Hola,")
        print()
        print("Gracias por registrarte en Gastos App.")
        print("Para confirmar tu cuenta, haz clic en el siguiente enlace:")
        print()
        print(f"  {confirmation_url}")
        print()
        print("Este enlace expirará en 24 horas.")
        print()
        print("Si no creaste esta cuenta, ignora este mensaje.")
        print("=" * 70)
        return True
    
    # Production mode: send real email via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Confirma tu cuenta - Gastos App"
        msg["From"] = smtp_config["from_addr"]
        msg["To"] = to_email
        
        # Plain text version
        text = f"""
Hola,

Gracias por registrarte en Gastos App.

Para confirmar tu cuenta, haz clic en el siguiente enlace:

{confirmation_url}

Este enlace expirará en 24 horas.

Si no creaste esta cuenta, ignora este mensaje.

Saludos,
Equipo de Gastos App
"""
        
        # HTML version
        html = f"""
<html>
<head></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4CAF50;">¡Bienvenido a Gastos App!</h2>
        
        <p>Hola,</p>
        
        <p>Gracias por registrarte en Gastos App.</p>
        
        <p>Para confirmar tu cuenta y empezar a usarla, haz clic en el botón de abajo:</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{confirmation_url}" 
               style="background-color: #4CAF50; 
                      color: white; 
                      padding: 12px 30px; 
                      text-decoration: none; 
                      border-radius: 5px;
                      display: inline-block;">
                Confirmar mi cuenta
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            O copia y pega este enlace en tu navegador:<br>
            <a href="{confirmation_url}" style="color: #4CAF50;">{confirmation_url}</a>
        </p>
        
        <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            Este enlace expirará en 24 horas.<br>
            Si no creaste esta cuenta, ignora este mensaje.
        </p>
    </div>
</body>
</html>
"""
        
        part1 = MIMEText(text, "plain", "utf-8")
        part2 = MIMEText(html, "html", "utf-8")
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via SMTP
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"❌ Error sending confirmation email: {e}")
        return False


def send_password_reset_email(to_email: str, reset_url: str):
    """
    Send password reset email with a secure token link.
    (Future feature - placeholder for now)
    
    Args:
        to_email: recipient email address
        reset_url: full URL to reset password
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # TODO: implement password reset email
    pass
