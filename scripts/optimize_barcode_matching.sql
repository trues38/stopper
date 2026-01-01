-- STOPPER 바코드 매칭 최적화
-- 1. 정규화 컬럼 추가

ALTER TABLE foods
ADD COLUMN IF NOT EXISTS name_norm TEXT,
ADD COLUMN IF NOT EXISTS manufacturer_norm TEXT,
ADD COLUMN IF NOT EXISTS tokens TEXT[];

-- 2. pg_trgm 확장 설치 (유사도 검색)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 3. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_foods_manufacturer_norm ON foods(manufacturer_norm);
CREATE INDEX IF NOT EXISTS idx_foods_tokens_gin ON foods USING GIN(tokens);
CREATE INDEX IF NOT EXISTS idx_foods_name_norm_trgm ON foods USING GIN(name_norm gin_trgm_ops);

-- 4. 바코드 매칭 결과 테이블
CREATE TABLE IF NOT EXISTS barcode_matches (
    id SERIAL PRIMARY KEY,
    barcode VARCHAR(20) NOT NULL,
    food_id INTEGER REFERENCES foods(id),
    mfds_name TEXT,
    mfds_company TEXT,
    confidence FLOAT,
    status VARCHAR(20),  -- 'AUTO', 'REVIEW', 'FAIL'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_barcode_matches_barcode ON barcode_matches(barcode);
CREATE INDEX IF NOT EXISTS idx_barcode_matches_food_id ON barcode_matches(food_id);
CREATE INDEX IF NOT EXISTS idx_barcode_matches_status ON barcode_matches(status);
