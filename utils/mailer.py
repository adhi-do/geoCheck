import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_magic_link_email(to_email: str, magic_link: str) -> tuple[bool, str]:
    """
    Send a magic login link email using Python's built-in smtplib and MIME libraries.
    Configuration is read from environment variables (.env):
      - MAIL_SERVER (e.g., smtp.gmail.com)
      - MAIL_PORT (e.g., 587 or 465)
      - MAIL_USERNAME (e.g., your_email@gmail.com)
      - MAIL_PASSWORD (e.g., app password)
      - MAIL_USE_TLS (True/False)
      - MAIL_USE_SSL (True/False)

    :param to_email: Recipient student's email address
    :param magic_link: Fully-qualified verification URL
    :return: (success: bool, status_message: str)
    """
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))
    mail_username = os.getenv("MAIL_USERNAME", "").strip()
    mail_password = os.getenv("MAIL_PASSWORD", "").strip()
    mail_use_tls = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    mail_use_ssl = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "yes")

    subject = "Workbase Attendance - Your Magic Login Link"

    # Construct MIME multipart email message (plain text + html fallback)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Workbase Attendance <{mail_username}>" if mail_username else "Workbase Attendance"
    msg["To"] = to_email

    plain_text = f"""Hello,

You requested a login link for the Workbase Attendance portal.
Click or copy the link below into your browser to log in (valid for 15 minutes):

{magic_link}

If you did not request this link, you can safely ignore this email.
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
    <div style="max-width: 520px; margin: 20px auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="border-bottom: 2px solid #3b82f6; padding-bottom: 16px; margin-bottom: 24px;">
            <h2 style="color: #1e293b; margin: 0; font-size: 22px;">Workbase Attendance</h2>
        </div>
        <p style="color: #334155; font-size: 15px; line-height: 1.6;">Hello,</p>
        <p style="color: #334155; font-size: 15px; line-height: 1.6;">
            We received a login request for your student account. Click the button below to sign in directly without a password.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{magic_link}" style="background-color: #2563eb; color: #ffffff; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; display: inline-block; font-size: 15px;">
                Log In to Workbase
            </a>
        </div>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
            <strong>Note:</strong> This link is single-use and will expire in <strong>15 minutes</strong>.
        </p>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5; word-break: break-all;">
            If the button doesn't work, copy and paste this URL into your browser:<br>
            <a href="{magic_link}" style="color: #2563eb;">{magic_link}</a>
        </p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">
            If you did not request this login link, you can safely disregard this message.
        </p>
    </div>
</body>
</html>
"""

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # When MAIL_PASSWORD is empty, notify and print to console so development is not blocked
    if not mail_password or not mail_username:
        print("\n" + "=" * 65)
        print("[SMTP NOTICE] MAIL_PASSWORD or MAIL_USERNAME is not set in .env")
        print(f"Recipient: {to_email}")
        print(f"Magic Link: {magic_link}")
        print("=" * 65 + "\n")
        return True, "Development notice: SMTP credentials not set in .env. Magic link has been printed to the server terminal."

    try:
        if mail_use_ssl:
            with smtplib.SMTP_SSL(mail_server, mail_port, timeout=10) as server:
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
                if mail_use_tls:
                    server.starttls()
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())

        return True, f"Magic link successfully sent to {to_email}."
    except Exception as e:
        # Log to terminal for debugging and test fallback
        print(f"[SMTP ERROR] Could not deliver email to {to_email}: {e}")
        print(f"[MAGIC LINK FALLBACK]: {magic_link}")
        return False, f"Failed to send email via SMTP ({e}). Check your server logs."
