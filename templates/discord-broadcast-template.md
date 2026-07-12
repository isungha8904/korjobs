# 디스코드 배포판 템플릿 (`broadcast/YYYY-MM-DD-discord.json`)

`/format-discord` 컴포넌트가 이 규칙대로 JSON을 생성합니다. 정확한 필드 계약은 [data/SCHEMA.md](../data/SCHEMA.md)의 `broadcast/<date>-discord.json` 섹션을 따르세요.

## [규칙]

- **섹션 1개 = 메시지 1개 = 임베드 1개.** 정확히 6개, 아래 순서 고정:
  1. `top3` — 🔥 오늘의 핵심 3가지 (색 `15158332`)
  2. `news` — 📰 뉴스 더보기 (색 `3447003`)
  3. `videos` — 🎥 볼 만한 영상 (색 `15105570`)
  4. `threads` — 🧵 Threads 화제 (색 `10181046`)
  5. `career` — 💼 커리어·채용 시그널 (색 `3066993`)
  6. `glossary` — 📖 용어 한 스푼 (색 `9807270`)
- **description ≤ 3,800자** (초과 시 항목 수를 줄일 것 — 절대 3,800자를 넘기지 않기).
- 카톡판과 달리 **마크다운 링크 `[제목](URL)` 허용** — 임베드 안 링크는 미리보기 카드를 만들지 않으므로 적극 사용.
- `content`(일반 텍스트)는 `top3` 메시지에만 브리핑 헤더로 넣고 나머지는 생략.
- 링크 규칙은 공통: 개별 기사/공식 발표 직접 URL만, 영상은 실제 watch URL만.
- `status`는 항상 `"draft"`로 생성 (발송 여부는 봇이 기록).
- 파일은 UTF-8, 한글이 이스케이프되지 않게 (`ensure_ascii=false` 상당).

## [스켈레톤]

```json
{
  "date": "YYYY-MM-DD",
  "digest_url": "https://github.com/isungha8904/korjobs/blob/main/digests/YYYY-MM-DD.md",
  "status": "draft",
  "messages": [
    {
      "key": "top3",
      "content": "🗞️ **IT·AI 뉴스 브리핑** · YYYY-MM-DD(요일) · 🎯 중급 개발자 + 입문자 믹스",
      "embed": {
        "title": "🔥 오늘의 핵심 3가지",
        "description": "**1) [제목]**\n[1~2줄 해설]\n👉 [왜 중요]\n[원문 보기](URL)\n\n**2) [제목]**\n...\n\n**3) [제목]**\n...",
        "url": "https://github.com/isungha8904/korjobs/blob/main/digests/YYYY-MM-DD.md",
        "color": 15158332,
        "footer": "korjobs · YYYY-MM-DD"
      }
    },
    {
      "key": "news",
      "embed": {
        "title": "📰 뉴스 더보기",
        "description": "🚀 **[제목]**\n[해설] 👉 [왜 중요]\n[원문 보기](URL)\n\n🔧 **[제목]**\n...\n\n🌱 **[입문 친화 뉴스]**\n...",
        "color": 3447003,
        "footer": "korjobs · YYYY-MM-DD"
      }
    },
    {
      "key": "videos",
      "embed": {
        "title": "🎥 볼 만한 영상 (실습·튜토리얼 위주 · 최근 2주)",
        "description": "🌱 **[영상 제목]** · 추정 [게시일]\n- [다루는 내용]\n[▶ 보기](watch URL)\n\n🔧 **[영상 제목]** · 추정 [게시일]\n...",
        "color": 15105570,
        "footer": "게시일 추정 — 배포 전 확인 · korjobs · YYYY-MM-DD"
      }
    },
    {
      "key": "threads",
      "embed": {
        "title": "🧵 Threads 화제",
        "description": "🔹 **@[핸들]**\n[요지]\n[🔗 보기](URL)\n\n🔹 **#[해시태그] 트렌드**\n...",
        "color": 10181046,
        "footer": "korjobs · YYYY-MM-DD"
      }
    },
    {
      "key": "career",
      "embed": {
        "title": "💼 커리어·채용 시그널",
        "description": "📌 **[뉴스 흐름]** → [채용/스킬 의미]\n▶ 배워두면 좋은 것: [스킬]\n\n📌 ...\n\n🧭 **오늘의 실무 팁:** [바로 해볼 액션 1개]",
        "color": 3066993,
        "footer": "korjobs · YYYY-MM-DD"
      }
    },
    {
      "key": "glossary",
      "embed": {
        "title": "📖 용어 한 스푼",
        "description": "· **[용어]** = [한 줄 정의]\n· **[용어]** = [한 줄 정의]\n· **[용어]** = [한 줄 정의]\n\n이번 주도 화이팅! 🚀",
        "color": 9807270,
        "footer": "korjobs · YYYY-MM-DD"
      }
    }
  ],
  "edit_log": [],
  "sent_at": null,
  "announce_message_ids": []
}
```
