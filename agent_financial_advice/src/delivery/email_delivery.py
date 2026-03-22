"""
Email delivery: Gmail SMTP (default) or SendGrid.
Converts the Markdown newsletter to HTML before sending.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import markdown as md

from src.analysis.recommender import Newsletter
from src.utils.logger import logger


class EmailDelivery:
    def __init__(
        self,
        provider: str = "gmail",
        gmail_user: str = "",
        gmail_app_password: str = "",
        sendgrid_api_key: str = "",
    ):
        self.provider = provider
        self.gmail_user = gmail_user
        self.gmail_app_password = gmail_app_password
        self.sendgrid_api_key = sendgrid_api_key

    def send(self, newsletter: Newsletter, recipients: List[str]) -> bool:
        if not recipients:
            logger.warning("Email: no recipients configured")
            return False

        if self.provider == "sendgrid":
            return self._send_sendgrid(newsletter, recipients)
        return self._send_gmail(newsletter, recipients)

    def _send_gmail(self, newsletter: Newsletter, recipients: List[str]) -> bool:
        try:
            html_body = md.markdown(newsletter.markdown_body, extensions=["extra", "nl2br"])
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Georgia, serif; max-width: 700px; margin: auto; padding: 20px; color: #1a1a1a; }}
    h1 {{ color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 8px; }}
    h2 {{ color: #2c5f8a; margin-top: 24px; }}
    h3 {{ color: #1a3a5c; }}
    blockquote {{ background: #f4f8fb; border-left: 4px solid #2c5f8a; padding: 12px; margin: 16px 0; }}
    a {{ color: #2c5f8a; }}
    hr {{ border: none; border-top: 1px solid #dde4ec; margin: 24px 0; }}
    code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>
"""
            msg = MIMEMultipart("alternative")
            msg["Subject"] = newsletter.subject
            msg["From"] = self.gmail_user
            msg["To"] = ", ".join(recipients)

            msg.attach(MIMEText(newsletter.plain_text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.gmail_user, self.gmail_app_password)
                server.sendmail(self.gmail_user, recipients, msg.as_string())

            logger.info(f"Email sent via Gmail to {len(recipients)} recipient(s)")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Gmail authentication failed. Make sure you're using an App Password "
                "(not your main password). Enable it at: "
                "myaccount.google.com → Security → 2-Step Verification → App passwords"
            )
            return False
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return False

    def _send_sendgrid(self, newsletter: Newsletter, recipients: List[str]) -> bool:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, To

            html_body = md.markdown(newsletter.markdown_body, extensions=["extra"])
            message = Mail(
                from_email=("noreply@financial-agent.local", "Financial Agent"),
                subject=newsletter.subject,
                html_content=html_body,
                plain_text_content=newsletter.plain_text_body,
            )
            message.to = [To(r) for r in recipients]

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in (200, 202):
                logger.info(f"Email sent via SendGrid to {len(recipients)} recipient(s)")
                return True
            else:
                logger.error(f"SendGrid returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False
