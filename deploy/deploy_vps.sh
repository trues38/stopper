#!/bin/bash
# STOPPER VPS 배포 스크립트

set -e

VPS_HOST="root@141.164.35.214"
VPS_PATH="/opt/stopper"

echo "=== STOPPER VPS 배포 ==="

# 1. VPS에 디렉토리 생성
echo "[1/5] VPS 디렉토리 준비..."
ssh $VPS_HOST "mkdir -p $VPS_PATH/{backend,data,deploy}"

# 2. 파일 동기화
echo "[2/5] 파일 동기화..."
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude 'dist' \
    --exclude '.env' \
    /Users/js/Documents/stopper/backend/ $VPS_HOST:$VPS_PATH/backend/

rsync -avz --progress \
    /Users/js/Documents/stopper/data/ $VPS_HOST:$VPS_PATH/data/

rsync -avz --progress \
    /Users/js/Documents/stopper/deploy/ $VPS_HOST:$VPS_PATH/deploy/

# 3. Docker 빌드 및 실행
echo "[3/5] Docker 빌드 및 실행..."
ssh $VPS_HOST "cd $VPS_PATH/deploy && docker compose -f docker-compose.vps.yml down --remove-orphans 2>/dev/null || true"
ssh $VPS_HOST "cd $VPS_PATH/deploy && docker compose -f docker-compose.vps.yml up -d --build"

# 4. DB 초기화 (첫 배포시에만)
echo "[4/5] 데이터베이스 초기화..."
sleep 10  # PostgreSQL 시작 대기
ssh $VPS_HOST "docker exec stopper-api python -c '
import asyncio
import sys
sys.path.insert(0, \"/app/backend\")
from db.load_data import main
asyncio.run(main())
' 2>/dev/null || echo 'DB already initialized or loading...'"

# 5. 상태 확인
echo "[5/5] 상태 확인..."
sleep 3
ssh $VPS_HOST "curl -s http://localhost:8003/health"

echo ""
echo "=== 배포 완료! ==="
echo "API: http://141.164.35.214:8003"
echo "Health: http://141.164.35.214:8003/health"
