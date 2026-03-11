import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_message(chat_id: str, message: str) -> requests.Response | None:
    """텔레그램 Bot API로 메시지를 발송한다. 실패 시 None을 반환한다."""
    bot_token = settings.TELEGRAM_BOT_TOKEN

    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
        return None

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=5,
        )
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"텔레그램 알림 발송 실패: {e}")
        return None
