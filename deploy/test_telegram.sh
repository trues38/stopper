#!/bin/bash
# Telegram 알림 테스트 스크립트

TELEGRAM_BOT_TOKEN="8261139696:AAFCkSQWJn27KxNbEWj1ScKUNgs_LtD1MFI"
TELEGRAM_CHAT_ID="5991157652"

echo "📱 Telegram 알림 테스트 중..."

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="✅ STOPPER Telegram 알림 테스트

Health Check 시스템이 정상적으로 작동하고 있습니다.

- 컨테이너 모니터링: 활성화
- API Health Check: 활성화
- 자동 재시작: 활성화

Time: $(date '+%Y-%m-%d %H:%M:%S')
Server: 141.164.35.214" \
    -d parse_mode="HTML"

if [ $? -eq 0 ]; then
    echo "✅ Telegram 알림 전송 성공!"
else
    echo "❌ Telegram 알림 전송 실패"
fi
