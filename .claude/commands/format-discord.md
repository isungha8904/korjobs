---
description: data/<date>/*.json을 디스코드 Embed 배포판(broadcast/<date>-discord.json)으로 변환
argument-hint: [YYYY-MM-DD]
---

당신은 korjobs 파이프라인의 **디스코드 포맷팅** 컴포넌트입니다. `broadcast/<date>-discord.json` 만 담당합니다 — `data/<date>/*.json`이나 `digests/`, 다른 `broadcast/` 파일은 건드리지 마세요.

날짜: `$1` (생략 시 사용자에게 물어보거나 오늘 날짜 사용).

1. `data/<date>/news.json`, `videos.json`, `threads.json`, `career.json`을 읽으세요. 하나라도 없으면 어떤 `/curate-*` 또는 `/career-signal` 커맨드를 먼저 실행해야 하는지 사용자에게 알려주고, 빈 자리를 지어내지 마세요. (카톡판·GitHub판과 독립적으로 실행 가능합니다 — 원본은 같은 `data/` JSON입니다.)
2. [templates/discord-broadcast-template.md](../../templates/discord-broadcast-template.md)의 규칙과 스켈레톤을 그대로 따르세요: **6개 고정 key/순서/제목/색상**, `description` **≤3,800자**(초과 시 항목 축소), 카톡과 달리 `[제목](URL)` 마크다운 링크 허용, `content` 헤더는 `top3`에만.
3. `digest_url`은 `https://github.com/isungha8904/korjobs/blob/main/digests/<date>.md` 형태로 채우세요.
4. `status: "draft"`, `edit_log: []`, `sent_at: null`, `announce_message_ids: []`로 두고 `broadcast/<date>-discord.json`에 UTF-8(한글 이스케이프 없이)로 씁니다. 정확한 필드 계약은 [data/SCHEMA.md](../../data/SCHEMA.md)를 따르세요.
5. 작성 후 사용자에게 다음 단계를 안내하세요: `python bot/send_discord.py <date>` 실행 → 디스코드 승인 채널에서 ✅승인/✏️편집/❌반려.

`data/<date>/*.json`, `digests/`, 카톡판은 다른 컴포넌트 담당이므로 수정하지 마세요. 이 파일의 `status`·`edit_log`·발송 메타데이터는 봇이 기록하므로 건드리지 마세요.
