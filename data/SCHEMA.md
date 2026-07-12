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

## 검증 규칙 (모든 컴포넌트 공통)
- 링크는 항상 원문/공식 발표 직접 URL. 언론사 홈·뉴스 모음·채널 홈·재생목록 금지.
- 확인 안 된 수치(조회수·게시일 등)는 날조 금지 — 모르면 "추정" 표기 또는 생략.
- 반복 용어는 `../glossary.md#앵커` 링크. 새 용어면 `glossary.md`에 추가하는 것도 검토.
