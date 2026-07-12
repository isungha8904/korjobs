---
description: 다이제스트 날짜에 맞는 Threads 화제를 큐레이션해 data/<date>/threads.json 작성
argument-hint: [YYYY-MM-DD]
---

당신은 korjobs 다이제스트 파이프라인의 **Threads 큐레이션** 컴포넌트입니다. `data/<date>/threads.json` **만** 담당합니다 — `data/<date>/` 아래 다른 파일은 건드리지 마세요.

날짜: `$1` (생략 시 사용자에게 물어보거나 오늘 날짜 사용).

1. [README.md](../../README.md)를 확인하세요 — Threads 항목은 개발자 커뮤니티 화제(공식 AI 계정, #AICoding 같은 트렌드 해시태그, 주목할 만한 플랫폼 통합 소식)를 다룹니다.
2. 화제 계정/핸들, 트렌드 해시태그, 또는 개발자 관련 플랫폼 통합 뉴스 2~4개를 찾으세요.
3. 각 항목은 직접 URL(프로필, 태그 페이지, 혹은 해당 소식을 다룬 기사)이 있어야 합니다.
4. 결과를 [data/SCHEMA.md](../../data/SCHEMA.md)의 스키마 그대로 `data/<date>/threads.json`에 씁니다.

`digests/`, `broadcast/` 등 다른 파일은 다른 컴포넌트 담당이므로 건드리지 마세요.
