---
description: data/<date>/*.json을 조립해 GitHub용 digests/<date>.md 생성 및 인덱스 업데이트
argument-hint: [YYYY-MM-DD]
---

당신은 korjobs 파이프라인의 **다이제스트 조립** 컴포넌트입니다. `digests/<date>.md`와 `digests/README.md`의 인덱스 행만 담당합니다 — `data/<date>/*.json`(큐레이션 컴포넌트 담당)이나 `broadcast/`는 건드리지 마세요.

날짜: `$1` (생략 시 사용자에게 물어보거나 오늘 날짜 사용).

1. `data/<date>/news.json`, `videos.json`, `threads.json`, `career.json`을 읽으세요. 하나라도 없으면 어떤 `/curate-*` 또는 `/career-signal` 커맨드를 먼저 실행해야 하는지 사용자에게 알려주고, 빈 자리를 지어내지 마세요.
2. [templates/digest-template.md](../../templates/digest-template.md) 구조를 그대로 따르세요: Top 3(`news.json`에서 `top3_candidate`로 표시된 항목 중 선택), 📰 뉴스, 🎥 영상, 🧵 Threads, 💼 커리어·채용 시그널 표, 🧭 실무 팁, 출처 footer.
3. 반복되는 용어는 [glossary.md](../../glossary.md) 앵커로 링크하세요.
4. `digests/<date>.md`에 씁니다.
5. `digests/README.md` 표 맨 위에 한 줄 추가(날짜, 한 줄 요약, 읽기 시간 추정, 다이제스트 링크, 카톡판 링크 — `/format-kakao`가 아직 실행 안 됐어도 예상 경로 `../broadcast/<date>-kakao.txt`를 사용).
6. 루트 [README.md](../../README.md)의 "최근 회차" 아래에 한 줄 추가.

`data/<date>/*.json`이나 `broadcast/*.txt`는 다른 컴포넌트 담당이므로 수정하지 마세요.
