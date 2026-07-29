"""Logic Apps 메일 연동을 수동으로 확인하는 개발용 스크립트."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

AUTHORIZED_TEST_RECIPIENT = "alfzm102435@gmail.com"


def main():
    url = os.getenv("LOGIC_APP_URL_MAIL")
    recipient = os.getenv(
        "TEST_EMAIL_RECIPIENT",
        AUTHORIZED_TEST_RECIPIENT,
    ).strip()

    if not url:
        raise RuntimeError("LOGIC_APP_URL_MAIL 환경변수가 필요합니다.")
    if recipient != AUTHORIZED_TEST_RECIPIENT:
        raise RuntimeError("허용된 테스트 수신자에게만 메일을 보낼 수 있습니다.")

    response = requests.post(
        url,
        json={
            "email": recipient,
            "subject": "[IEUM] 메일 연동 테스트",
            "body": "<p>환경변수 기반 Logic Apps 연동 테스트입니다.</p>",
        },
        timeout=10,
    )
    response.raise_for_status()
    print("[성공] 테스트 메일을 발송했습니다.")


if __name__ == "__main__":
    main()
