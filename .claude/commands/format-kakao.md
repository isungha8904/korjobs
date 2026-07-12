---
description: data/<date>/*.json을 카카오톡 플레인 텍스트 배포판(broadcast/<date>-kakao.txt)으로 변환
argument-hint: [YYYY-MM-DD]
---

당신은 korjobs 파이프라인의 **카톡 포맷팅** 컴포넌트입니다. `broadcast/<date>-kakao.txt` 만 담당합니다 — `data/<date>/*.json`이나 `digests/`는 건드리지 마세요.

날짜: `$1` (생략 시 사용자에게 물어보거나 오늘 날짜 사용).

1. `data/<date>/news.json`, `videos.json`, `threads.json`, `career.json`을 읽으세요. 하나라도 없으면 어떤 `/curate-*` 또는 `/career-signal` 커맨드를 먼저 실행해야 하는지 사용자에게 알려주고, 빈 자리를 지어내지 마세요. (이 컴포넌트는 `digests/<date>.md`가 아직 조립되지 않았어도 독립적으로 실행할 수 있습니다 — 두 컴포넌트 모두 같은 `data/` JSON을 원본으로 씁니다.)
2. [templates/kakao-broadcast-template.txt](../../templates/kakao-broadcast-template.txt)의 규칙을 그대로 따르세요: 마크다운 금지(`#`, 표, `[]()`, `<details>` 사용 금지), 링크는 전체 URL을 한 줄에, 6블록으로 쪼개고 `───── ✂️ 여기서 끊어 보내기 (n/6) ─────`로 구분.
3. 상단 "🔗 상세 아카이브" 링크는 `https://github.com/isungha8904/korjobs/blob/main/digests/<date>.md` 형태로 채우세요(아직 main에 없어도 조립이 끝나면 유효해질 경로).
4. `broadcast/<date>-kakao.txt`에 씁니다.

`data/<date>/*.json`이나 `digests/`는 다른 컴포넌트 담당이므로 수정하지 마세요.
