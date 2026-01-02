#!/bin/bash
# STOPPER 자동 복구 스크립트
# VPS에서 5분마다 실행

LOG_FILE="/var/log/stopper-health.log"
COMPOSE_FILE="/opt/stopper/deploy/docker-compose.vps.yml"
MAX_RETRIES=3

# Telegram 설정
TELEGRAM_BOT_TOKEN="8261139696:AAFCkSQWJn27KxNbEWj1ScKUNgs_LtD1MFI"
TELEGRAM_CHAT_ID="5991157652"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_telegram() {
    local message="$1"
    local emoji="$2"

    # Telegram 메시지 전송
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="${emoji} STOPPER VPS Alert

${message}

Time: $(date '+%Y-%m-%d %H:%M:%S')
Server: 141.164.35.214" \
        -d parse_mode="HTML" > /dev/null
}

check_container() {
    local container=$1
    if ! docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        return 1
    fi
    return 0
}

check_api_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health)
    if [ "$response" = "200" ]; then
        return 0
    fi
    return 1
}

restart_service() {
    log "⚠️  서비스 재시작 시도..."
    cd /opt/stopper/deploy
    docker compose -f docker-compose.vps.yml restart
    sleep 10
}

# 1. 컨테이너 상태 확인
if ! check_container "stopper-db"; then
    log "❌ PostgreSQL 컨테이너 다운됨"
    send_telegram "PostgreSQL 컨테이너가 다운되었습니다. 재시작을 시도합니다." "🔴"
    restart_service
fi

if ! check_container "stopper-api"; then
    log "❌ API 컨테이너 다운됨"
    send_telegram "STOPPER API 컨테이너가 다운되었습니다. 재시작을 시도합니다." "🔴"
    restart_service
fi

# 2. API Health Check
retry=0
while [ $retry -lt $MAX_RETRIES ]; do
    if check_api_health; then
        log "✅ 모든 서비스 정상"
        exit 0
    fi

    log "⚠️  API 응답 없음 (시도 $((retry+1))/$MAX_RETRIES)"
    retry=$((retry+1))
    sleep 5
done

# 3. 재시작 시도
log "❌ API Health Check 실패 - 재시작 필요"
send_telegram "API Health Check가 ${MAX_RETRIES}회 실패했습니다. 서비스를 재시작합니다." "⚠️"
restart_service

# 4. 재시작 후 확인
sleep 10
if check_api_health; then
    log "✅ 재시작 성공"
    send_telegram "서비스가 정상적으로 재시작되었습니다." "✅"
else
    log "🚨 재시작 실패 - 수동 확인 필요!"
    send_telegram "🚨 긴급: 서비스 재시작에 실패했습니다!

수동 확인이 필요합니다.
SSH: ssh root@141.164.35.214
Logs: docker logs stopper-api" "🚨"
fi
