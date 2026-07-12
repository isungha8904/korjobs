---
description: 다이제스트 날짜에 맞는 IT/AI 뉴스를 큐레이션해 data/<date>/news.json 작성
argument-hint: [YYYY-MM-DD]
---

당신은 korjobs 다이제스트 파이프라인의 **뉴스 큐레이션** 컴포넌트입니다. `data/<date>/news.json` **만** 담당합니다 — `data/<date>/` 아래 다른 파일은 건드리지 마세요.

날짜: `$1` (생략 시 사용자에게 물어보거나 오늘 날짜 사용).

1. [README.md](../../README.md)의 선정 원칙(화제성/실용성 우선, 직접 링크만, 레벨 믹스, 커리어 시그널 관점)과 [glossary.md](../../glossary.md)의 기존 용어를 확인하세요.
2. 중급 한국 개발자에게 유의미한 최신 IT/AI 뉴스를 검색합니다(프론티어 모델, 개발 툴링, 인프라, 국내 테크업계/채용 시그널). 입문자용(🌱) 뉴스도 1~2개 섞으세요.
3. 각 항목은 **개별 기사 본문 또는 공식 발표** 직접 URL로 연결하세요 — 언론사 홈이나 뉴스 모음 페이지는 금지입니다.
4. 가장 화제성 있는 2~4개 항목에 `top3_candidate: true`를 표시하세요(최종 Top 3는 조립 단계에서 이 후보 중 선택).
5. 결과를 [data/SCHEMA.md](../../data/SCHEMA.md)의 스키마 그대로 `data/<date>/news.json`에 씁니다.

`digests/`, `broadcast/` 등 다른 파일은 다른 컴포넌트 담당이므로 건드리지 마세요.
