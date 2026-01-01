-- 스탑퍼 PostgreSQL 스키마

-- 1. 가공식품 테이블 (244K)
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY,
    food_code VARCHAR(30) UNIQUE,
    name VARCHAR(300) NOT NULL,
    manufacturer VARCHAR(200),
    category_large VARCHAR(100),
    category_medium VARCHAR(100),
    calories DECIMAL(10,2) DEFAULT 0,
    protein DECIMAL(10,2) DEFAULT 0,
    fat DECIMAL(10,2) DEFAULT 0,
    carbohydrate DECIMAL(10,2) DEFAULT 0,
    sugar DECIMAL(10,2) DEFAULT 0,
    sodium DECIMAL(10,2) DEFAULT 0,
    saturated_fat DECIMAL(10,2) DEFAULT 0,
    serving_size VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_foods_name ON foods USING gin(to_tsvector('simple', name));
CREATE INDEX IF NOT EXISTS idx_foods_category ON foods(category_large);
CREATE INDEX IF NOT EXISTS idx_foods_protein ON foods(protein DESC);
CREATE INDEX IF NOT EXISTS idx_foods_calories ON foods(calories);
CREATE INDEX IF NOT EXISTS idx_foods_sugar ON foods(sugar);

-- 2. 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) UNIQUE,
    kakao_id VARCHAR(100) UNIQUE,
    nickname VARCHAR(50),
    goal_type VARCHAR(20) DEFAULT 'maintain',
    calorie_goal INTEGER DEFAULT 2000,
    protein_goal INTEGER DEFAULT 60,
    sugar_limit INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_fingerprint ON users(fingerprint);

-- 3. 일일 기록 테이블
CREATE TABLE IF NOT EXISTS daily_records (
    id SERIAL PRIMARY KEY,
    user_fingerprint VARCHAR(64),
    food_id INTEGER REFERENCES foods(id),
    quantity DECIMAL(5,2) DEFAULT 1,
    meal_type VARCHAR(20),
    calories DECIMAL(10,2),
    protein DECIMAL(10,2),
    sugar DECIMAL(10,2),
    sodium DECIMAL(10,2),
    recorded_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_user_date ON daily_records(user_fingerprint, recorded_date);

-- 4. 조합 테이블 (JSONB - Neo4j 마이그레이션 대비)
--
-- JSON 구조:
-- {
--   "id": "combo_20260101_001",      -- 문자열 ID
--   "author_id": "user_anon_123",    -- 문자열 author
--   "items": [{"food_id": "food_123", "name": "...", "qty": 1}],
--   "intent": {"goal": "bulk", "target_protein": 50},
--   "result": {"calories": 520, "protein": 52, "sugar": 8},
--   "signals": {"worked": null, "repeat_count": 0, "next_combo_hint": null}
-- }
--
CREATE TABLE IF NOT EXISTS combinations (
    id SERIAL PRIMARY KEY,
    combo_id VARCHAR(50) UNIQUE NOT NULL,  -- 문자열 ID (combo_YYYYMMDD_NNN)
    name VARCHAR(100) NOT NULL,
    description TEXT,
    author_id VARCHAR(64) NOT NULL,  -- 문자열 (user_anon_xxx 또는 user_kakao_xxx)
    items JSONB NOT NULL,            -- [{food_id, name, qty, calories, protein, sugar}]
    intent JSONB NOT NULL,           -- {goal, target_protein, limit_sugar}
    result JSONB NOT NULL,           -- {calories, protein, sugar, percent_of_daily}
    signals JSONB DEFAULT '{"worked": null, "repeat_count": 0, "next_combo_hint": null}',
    tags TEXT[],
    likes_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    is_official BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_combinations_combo_id ON combinations(combo_id);
CREATE INDEX IF NOT EXISTS idx_combinations_likes ON combinations(likes_count DESC);
CREATE INDEX IF NOT EXISTS idx_combinations_tags ON combinations USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_combinations_intent ON combinations USING gin(intent);
CREATE INDEX IF NOT EXISTS idx_combinations_items ON combinations USING gin(items);
CREATE INDEX IF NOT EXISTS idx_combinations_author ON combinations(author_id);

-- 5. 추천 테이블
CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    combination_id INTEGER REFERENCES combinations(id) ON DELETE CASCADE,
    user_fingerprint VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(combination_id, user_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_likes_combination ON likes(combination_id);
