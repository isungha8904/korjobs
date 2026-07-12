# 데이터 계약 (Data Contract)

각 컴포넌트(슬래시 커맨드)는 `data/<YYYY-MM-DD>/` 아래 자기 담당 JSON **하나만** 쓰고, 남의 파일은 읽기만 합니다.
이 계약만 지키면 팀원들이 서로 다른 브랜치에서 독립적으로 작업하고 머지할 수 있습니다.

```
data/<YYYY-MM-DD>/
├── news.json      ← /curate-news 가 씀
├── videos.json     ← /curate-videos 가 씀
├── threads.json    ← /curate-threads 가 씀
└── career.json      ← /career-signal 가 씀
```

`/assemble-digest`, `/format-kakao`는 위 4개를 **읽기만** 하고 자기 산출물(`digests/*.md`, `broadcast/*.txt`)을 씁니다. 서로의 산출물에는 의존하지 않으므로 두 커맨드도 병렬로 실행 가능합니다.

## news.json
```json
{
  "items": [
    {
      "title": "string",
      "level": "🌱 | 🔧 | 🚀",
      "tldr": "개발자 관점 한 줄 요약",
      "detail": "본문 (glossary 링크 포함 가능, ../glossary.md#앵커 형식)",
      "source_url": "개별 기사/공식 발표 직접 URL만 (집계/홈페이지 금지)",
      "top3_candidate": true
    }
  ]
}
```

## videos.json
```json
{
  "items": [
    {
      "title": "string",
      "level": "🌱 | 🔧 | 🚀",
      "tldr": "이 영상이 다루는 것 한 줄",
      "published_estimate": "예: 추정 ~3주 전 (게시일 확인 불가 시 반드시 '추정' 표기)",
      "runtime": "예: ~14분 (확인 불가 시 생략, 날조 금지)",
      "topics": ["다루는 내용 bullet", "..."],
      "learn": "이런 걸 배웁니다",
      "audience": "이런 사람에게",
      "url": "실제 영상 watch URL만 (youtube.com/watch?v=... — 채널/재생목록/집계 금지)"
    }
  ]
}
```
규칙: 최근 2주 이내 게시분만, 실습·튜토리얼 위주(뉴스요약 영상은 최소).

## threads.json
```json
{
  "items": [
    {
      "handle_or_tag": "@handle 또는 #hashtag",
      "summary": "무엇이 화제인지 한 줄",
      "url": "string"
    }
  ]
}
```

## career.json
```json
{
  "rows": [
    { "trend": "뉴스 흐름", "meaning": "채용/스킬 의미", "skills": "지금 배워두면 좋은 것" }
  ],
  "tip": "🧭 오늘의 실무 팁 — 오늘 바로 해볼 수 있는 액션 1개"
}
```

## broadcast/&lt;date&gt;-discord.json — 디스코드 배포판 계약

카톡판(txt, 사람이 소비)과 달리 이 파일은 **기계 간 계약**입니다: `/format-discord`가 생성하고, `bot/send_discord.py`(승인·발송 봇)가 읽고 변경합니다.

> **작성자가 둘인 파일**: `/format-discord`는 생성 시점에 `status: "draft"`로 쓰고, 봇은 승인 시점에 편집 내용·`status`·발송 메타데이터를 기록합니다. 두 시점이 순차라 충돌은 없습니다. 이 파일만은 "1파일 1작성자" 규칙의 예외입니다.

```json
{
  "date": "YYYY-MM-DD",
  "digest_url": "https://github.com/isungha8904/korjobs/blob/main/digests/<date>.md",
  "status": "draft",
  "messages": [
    {
      "key": "top3",
      "content": "🗞️ **IT·AI 뉴스 브리핑** · YYYY-MM-DD(요일) — top3에만 헤더로 사용, 나머지는 생략",
      "embed": {
        "title": "🔥 오늘의 핵심 3가지",
        "description": "**1) 제목**\n한 줄 해설\n👉 왜 중요\n[원문 보기](https://...)\n\n**2) ...**",
        "url": "https://github.com/isungha8904/korjobs/blob/main/digests/<date>.md",
        "color": 15158332,
        "footer": "korjobs · YYYY-MM-DD"
      }
    }
  ],
  "edit_log": [],
  "sent_at": null,
  "announce_message_ids": []
}
```

### 필드 규칙

| 필드 | 한도 | 비고 |
|------|------|------|
| `messages[].key` | enum | `top3` · `news` · `videos` · `threads` · `career` · `glossary` — **정확히 6개, 이 순서대로** 발송 |
| `messages[].content` | ≤ 2,000자 | 선택. `top3`에만 브리핑 헤더로 사용. content 안의 맨 URL은 미리보기 카드가 자동 생성되므로 원치 않으면 `<URL>`로 감싸기 |
| `embed.title` | ≤ 256자 | 섹션별 고정: 🔥 오늘의 핵심 3가지 / 📰 뉴스 더보기 / 🎥 볼 만한 영상 / 🧵 Threads 화제 / 💼 커리어·채용 시그널 / 📖 용어 한 스푼 |
| `embed.description` | **≤ 3,800자 (소프트)** | 디스코드 하드리밋은 4,096자지만 승인 봇의 편집 모달 입력 한도가 4,000자라 **3,800자를 넘기지 말 것** (편집 여유분). 마크다운 허용: `**굵게**`, `[제목](URL)`, `-` 불릿. 임베드 안 링크는 미리보기 카드를 만들지 않음 |
| `embed.url` | 유효 URL, 선택 | 제목을 클릭 가능하게 함. `top3`는 `digest_url` 사용 |
| `embed.color` | 10진수 int | 섹션별 고정: top3 `15158332`(0xE74C3C) · news `3447003`(0x3498DB) · videos `15105570`(0xE67E22) · threads `10181046`(0x9B59B6) · career `3066993`(0x2ECC71) · glossary `9807270`(0x95A5A6) |
| `embed.footer` | ≤ 2,048자 | 선택. `korjobs · YYYY-MM-DD` 권장 |
| `status` | enum | 라이프사이클: `draft` → `sent` 또는 `rejected`. 봇만 변경 |
| `edit_log[]` | — | 봇이 기록: `{ "key": "...", "editor": "유저명", "edited_at": "ISO시각" }` |
| `sent_at` / `announce_message_ids` | — | 봇이 발송 성공 시 기록 |

의도적 단순화: `fields[]`를 쓰지 않고 **description 단일 문단만** 사용합니다 — 승인 봇의 편집 모달 입력 1개에 섹션 전체가 들어가야 하기 때문입니다.

## 검증 규칙 (모든 컴포넌트 공통)
- 링크는 항상 원문/공식 발표 직접 URL. 언론사 홈·뉴스 모음·채널 홈·재생목록 금지.
- 확인 안 된 수치(조회수·게시일 등)는 날조 금지 — 모르면 "추정" 표기 또는 생략.
- 반복 용어는 `../glossary.md#앵커` 링크. 새 용어면 `glossary.md`에 추가하는 것도 검토.
