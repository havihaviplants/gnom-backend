-- schema.sql

-- 사용자 테이블
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 분석 대상자(상대방) 테이블
CREATE TABLE target_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    nickname TEXT,
    relationship_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 상대방 메시지 기록
CREATE TABLE message_logs (
    id SERIAL PRIMARY KEY,
    target_user_id INTEGER REFERENCES target_users(id),
    raw_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 감정 분석 결과
CREATE TABLE emotion_results (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES message_logs(id),
    emoji_summary TEXT,
    emotion_keywords TEXT[],
    core_analysis TEXT,
    tone_analysis TEXT,
    final_comment TEXT,
    is_premium BOOLEAN DEFAULT FALSE
);
