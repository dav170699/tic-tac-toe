"""
WhatsApp delivery via Twilio API.
Splits messages longer than 4000 chars into multiple parts.
"""
from typing import List

from src.analysis.recommender import Newsletter
from src.utils.logger import logger

MAX_WHATSAPP_CHARS = 4000


class WhatsAppDelivery:
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number  # e.g. "whatsapp:+14155238886"

    def send(self, newsletter: Newsletter, recipients: List[str]) -> bool:
        if not recipients:
            logger.warning("WhatsApp: no recipients configured")
            return False

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
        except ImportError:
            logger.error("twilio package not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Twilio client init failed: {e}")
            return False

        text = newsletter.plain_text_body
        chunks = self._split_message(text, newsletter.subject)
        success = True

        for recipient in recipients:
            for i, chunk in enumerate(chunks):
                try:
                    client.messages.create(
                        body=chunk,
                        from_=self.from_number,
                        to=recipient,
                    )
                    logger.debug(f"WhatsApp part {i+1}/{len(chunks)} sent to {recipient}")
                except Exception as e:
                    logger.error(f"WhatsApp send failed (part {i+1} to {recipient}): {e}")
                    success = False

        if success:
            logger.info(f"WhatsApp: sent {len(chunks)} message(s) to {len(recipients)} recipient(s)")
        return success

    def _split_message(self, text: str, subject: str) -> List[str]:
        if len(text) <= MAX_WHATSAPP_CHARS:
            return [text]

        # Split into chunks, preserving paragraphs
        paragraphs = text.split("\n\n")
        chunks = []
        current = f"📊 *{subject}*\n\n"

        for para in paragraphs:
            if len(current) + len(para) + 2 > MAX_WHATSAPP_CHARS:
                if current.strip():
                    chunks.append(current.strip())
                current = para + "\n\n"
            else:
                current += para + "\n\n"

        if current.strip():
            chunks.append(current.strip())

        # Add part indicators
        if len(chunks) > 1:
            chunks = [
                f"[{i+1}/{len(chunks)}] {chunk}" for i, chunk in enumerate(chunks)
            ]

        return chunks
