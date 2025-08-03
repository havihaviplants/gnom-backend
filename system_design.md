# Gnom AI – 감정 분석 앱 시스템 설계서 (MVP v1)

## 1. 앱 개요
- 사용자가 상대방의 메시지를 붙여넣으면, GPT가 감정/속마음/말투를 분석
- 감정 분석 결과는 감정 카드로 시각화되고 저장됨
- 무료 요약 분석과 유료 상세 분석으로 구분

---

## 2. 기능 구조

### 사용자 흐름
1. 메시지 입력 → 2. 관계 유형 선택 → 3. 분석 결과 출력 → 4. 저장 or 공유

### 감정 분석 구조
- GPT Prompt 설계: gpt_prompts.py
- 감정 결과 포맷: 감정 요약 + 속마음 해석 + 말투 분석 + 전체 문장

---

## 3. 데이터베이스 구조 (PostgreSQL)

### users
- 유저 정보: id, uuid, created_at

### target_users
- 관계별 대상 정보: nickname, relationship_type

### message_logs
- 붙여넣은 메시지 기록

### emotion_results
- GPT 분석 결과 (emoji_summary, emotion_keywords[], core_analysis 등)

---

## 4. 감정 카드 시스템

- emotion_cards.json 기반
- 각 분석 결과의 감정 키워드를 emotion_cards에서 매핑
- 감정 카드 = 이모지 + 키워드 + 설명

---

## 5. 기술 스택 제안

- 백엔드: FastAPI + PostgreSQL
- GPT: OpenAI GPT-4o API
- 프론트: React Native or Flutter
- 저장소: GitHub 비공개 저장소

---

## 6. 향후 확장

- 감정 히스토리 시각화 (히트맵, 타임라인)
- 감정 변화 탐지 / 리마인드 카드
- 감정 AI 리포트 PDF화 (프리미엄 전용)
