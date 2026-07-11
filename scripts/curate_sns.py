#!/usr/bin/env python3
"""korjobs SNS 큐레이션 파이프라인 — Apify(수집) + Claude Fable 5(선별·요약).

흐름:
  1. Apify 액터로 YouTube / TikTok / Instagram / Threads / Twitter(X) 게시물 수집
  2. 레포 원칙 파라미터로 필터 (최근 2주 · 조회수/반응 최소치 · 직접 URL · 키워드)
  3. Claude Fable 5가 후보를 선별·레벨 분류(🌱/🔧/🚀)·한국어 요약·커리어 시그널 작성
  4. GitHub 다이제스트용 마크다운 + 카톡 배포용 플레인텍스트 블록 생성

사용:
  export APIFY_TOKEN=apify_api_...
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 scripts/curate_sns.py                # 전체 실행
  python3 scripts/curate_sns.py --dry-run      # Apify 대신 내장 픽스처 사용
  python3 scripts/curate_sns.py --no-llm       # Fable 5 생략, 반응순 상위만 출력
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 파라미터 — 레포 큐레이션 원칙 (README 선정 원칙과 동기화)
# ---------------------------------------------------------------------------
PARAMS = {
    "recency_days": 14,        # 최근 2주 게시분만 (영상/SNS 공통 규칙)
    "min_views": 10_000,       # 조회수 지표가 있으면 이 이상만
    "min_engagement": 300,     # 조회수 지표가 없으면 좋아요+리포스트 합산 최소치
    "keywords": [              # 하나 이상 포함해야 후보로 인정
        "ai", "llm", "gpt", "claude", "gemini", "agent", "mcp", "rag",
        "인공지능", "에이전트", "코딩", "개발자", "챗gpt", "클로드",
    ],
    "max_candidates_per_platform": 40,  # LLM에 넘길 플랫폼당 후보 상한
    "picks_per_platform": 3,            # 최종 선별 목표(플랫폼당)
}

# ---------------------------------------------------------------------------
# Apify 액터 설정 — 액터 ID는 Apify Store에서 확인 후 교체 가능
# (액터마다 input/출력 필드가 달라서 normalize()가 여러 필드명을 흡수함)
# ---------------------------------------------------------------------------
ACTORS = {
    "youtube": {
        "actor_id": os.environ.get("APIFY_YOUTUBE_ACTOR", "streamers/youtube-scraper"),
        "run_input": lambda kw: {
            "searchKeywords": kw,
            "maxResults": 60,
            "sortingOrder": "views",
            "dateFilter": "month",   # 최근 한 달로 1차 컷 (2주 필터는 코드에서)
        },
    },
    "tiktok": {
        "actor_id": os.environ.get("APIFY_TIKTOK_ACTOR", "clockworks/tiktok-scraper"),
        "run_input": lambda kw: {
            "searchQueries": kw,
            "resultsPerPage": 60,
        },
    },
    "instagram": {
        "actor_id": os.environ.get("APIFY_INSTAGRAM_ACTOR", "apify/instagram-scraper"),
        "run_input": lambda kw: {
            "search": " OR ".join(kw[:3]),
            "searchType": "hashtag",
            "resultsType": "posts",
            "resultsLimit": 100,
        },
    },
    "threads": {
        "actor_id": os.environ.get("APIFY_THREADS_ACTOR", "curious_coder/threads-scraper"),
        "run_input": lambda kw: {"searchQueries": kw, "maxItems": 100},
    },
    "twitter": {
        "actor_id": os.environ.get("APIFY_TWITTER_ACTOR", "apidojo/tweet-scraper"),
        "run_input": lambda kw: {
            "searchTerms": kw,
            "maxItems": 100,
            "sort": "Top",
        },
    },
}

SEARCH_TERMS = ["AI coding", "Claude agent", "GPT-5.6", "AI 에이전트", "개발자 AI"]


# ---------------------------------------------------------------------------
# 1) 수집
# ---------------------------------------------------------------------------
def collect_from_apify(platforms: list[str]) -> list[dict]:
    from apify_client import ApifyClient  # 지연 임포트 (--dry-run이면 불필요)

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN 환경변수가 필요합니다 (--dry-run으로 픽스처 테스트 가능)")
    client = ApifyClient(token)

    items: list[dict] = []
    for platform, cfg in ((p, ACTORS[p]) for p in platforms):
        try:
            run = client.actor(cfg["actor_id"]).call(run_input=cfg["run_input"](SEARCH_TERMS))
            dataset = client.dataset(run["defaultDatasetId"]).list_items().items
            for raw in dataset:
                norm = normalize(platform, raw)
                if norm:
                    items.append(norm)
            print(f"[collect] {platform}: {len(dataset)}건 수집", file=sys.stderr)
        except Exception as e:  # 액터 하나 실패해도 나머지 플랫폼은 진행
            print(f"[collect] {platform} 실패: {e}", file=sys.stderr)
    return items


def _first(raw: dict, *keys):
    """액터별로 다른 필드명을 순서대로 시도."""
    for k in keys:
        v = raw.get(k)
        if v not in (None, "", 0):
            return v
    return None


def normalize(platform: str, raw: dict) -> dict | None:
    """액터별 상이한 출력 스키마 → 공통 스키마.

    흡수하는 필드명 예시 — YouTube(streamers): url/title/viewCount/date,
    TikTok(clockworks): webVideoUrl/text/playCount/diggCount/createTimeISO,
    Instagram: url/caption/videoViewCount/likesCount/timestamp,
    Threads: url/text/likeCount, X(apidojo): twitterUrl/fullText/viewCount/retweetCount.
    """
    url = _first(raw, "url", "postUrl", "twitterUrl", "webVideoUrl", "videoUrl", "link", "shortUrl")
    text = _first(raw, "text", "caption", "fullText", "content", "title", "desc") or ""
    published = _first(raw, "createdAt", "created_at", "timestamp", "publishedAt",
                       "date", "createTimeISO", "createTime", "uploadedAt", "uploadDate")
    views = _first(raw, "viewCount", "views", "playCount", "videoViewCount", "impressions")
    likes = _first(raw, "likeCount", "likes", "likesCount", "favouriteCount", "diggCount") or 0
    reposts = _first(raw, "repostCount", "retweetCount", "reposts", "sharesCount", "shareCount") or 0
    author = _first(raw, "username", "author", "ownerUsername", "userName", "handle",
                    "channelName", "channelUsername", "authorMeta")
    if isinstance(author, dict):
        author = _first(author, "username", "userName", "name", "screen_name", "nickName")
    if not url or not text:
        return None
    return {
        "platform": platform,
        "url": str(url),
        "author": str(author or "unknown"),
        "text": str(text)[:600],
        "published_at": str(published) if published else None,
        "views": int(views) if views else None,
        "likes": int(likes),
        "reposts": int(reposts),
    }


# ---------------------------------------------------------------------------
# 2) 필터 — "앞의 parameter" 적용
# ---------------------------------------------------------------------------
def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    for parser in (
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
        lambda s: datetime.fromtimestamp(float(s), tz=timezone.utc),
        lambda s: datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y"),  # 트위터 레거시 포맷
    ):
        try:
            dt = parser(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, OverflowError, OSError):
            continue
    return None


def apply_filters(items: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=PARAMS["recency_days"])
    seen_urls: set[str] = set()
    kept: list[dict] = []

    for it in items:
        # 직접 URL만 (플랫폼 게시물 링크가 아닌 것은 배제)
        if not it["url"].startswith("http"):
            continue
        # 중복 제거
        if it["url"] in seen_urls:
            continue
        # 최근 2주 — 게시일을 파싱할 수 없으면 '미확인'으로 배제 (날조 방지 원칙)
        dt = parse_dt(it["published_at"])
        if dt is None or dt < cutoff:
            continue
        # 조회수/반응 최소치
        if it["views"] is not None:
            if it["views"] < PARAMS["min_views"]:
                continue
        elif it["likes"] + it["reposts"] < PARAMS["min_engagement"]:
            continue
        # 키워드
        lowered = it["text"].lower()
        if not any(kw in lowered for kw in PARAMS["keywords"]):
            continue
        seen_urls.add(it["url"])
        kept.append(it)

    # 반응 높은 순 정렬 후 플랫폼당 상한 적용
    kept.sort(key=lambda x: (x["views"] or 0) * 1 + x["likes"] * 20 + x["reposts"] * 40, reverse=True)
    capped: list[dict] = []
    per_platform: dict[str, int] = {}
    for it in kept:
        n = per_platform.get(it["platform"], 0)
        if n < PARAMS["max_candidates_per_platform"]:
            capped.append(it)
            per_platform[it["platform"]] = n + 1
    return capped


# ---------------------------------------------------------------------------
# 3) Fable 5 선별·요약 (구조화 출력)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string",
                                 "enum": ["youtube", "tiktok", "instagram", "threads", "twitter"]},
                    "url": {"type": "string"},
                    "level": {"type": "string", "enum": ["🌱", "🔧", "🚀"]},
                    "title_ko": {"type": "string"},
                    "summary_ko": {"type": "string"},
                    "why_important_ko": {"type": "string"},
                },
                "required": ["platform", "url", "level", "title_ko", "summary_ko", "why_important_ko"],
                "additionalProperties": False,
            },
        },
        "career_signal_ko": {"type": "string"},
    },
    "required": ["picks", "career_signal_ko"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
너는 korjobs의 IT·AI 뉴스 큐레이터다. 독자는 한국의 중급(intermediate~moderate) 개발자이며,
입문자용 콘텐츠를 섞어 흥미를 유지한다.

선별 규칙:
- 후보 목록에 있는 게시물만 고른다. url은 후보의 url을 글자 그대로 복사한다. 새 URL을 만들지 않는다.
- 플랫폼당 최대 {picks}개, 레벨(🌱 입문/🔧 중급/🚀 심화)을 골고루 섞는다.
- 반응(조회수·좋아요·리포스트)이 높고, 개발자 실무·커리어와 관련 있는 것을 우선한다.
- summary_ko: 전문용어는 괄호로 짧게 풀어쓴 2~3문장 요약.
- why_important_ko: "그래서 내 코드/커리어에 뭐가 바뀌나" 관점 1~2문장.
- career_signal_ko: 선별한 게시물 전체에서 읽히는 한국 개발자 채용·스킬 시그널 2~3문장.
""".format(picks=PARAMS["picks_per_platform"])


def curate_with_fable(candidates: list[dict]) -> dict:
    import anthropic

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 또는 ant auth 프로필 사용
    payload = json.dumps(candidates, ensure_ascii=False, indent=1)

    # Fable 5: thinking은 항상 켜져 있으므로 thinking 파라미터를 보내지 않는다.
    # 안전 분류기가 요청을 거절할 수 있어(stop_reason: refusal) 서버측 폴백을 기본 탑재:
    # 거절 시 같은 호출 안에서 Opus 4.8이 이어받는다.
    with client.beta.messages.stream(
        model="claude-fable-5",
        max_tokens=32000,
        betas=["server-side-fallback-2026-06-01"],
        fallbacks=[{"model": "claude-opus-4-8"}],
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"오늘 날짜: {datetime.now().date()}\n\n후보 게시물 목록(JSON):\n{payload}",
        }],
    ) as stream:
        msg = stream.get_final_message()

    if msg.stop_reason == "refusal":
        detail = getattr(msg, "stop_details", None)
        sys.exit(f"모델이 요청을 거절했습니다 (fallback 포함 전체 거절): {detail}")

    text = next(b.text for b in msg.content if b.type == "text")
    result = json.loads(text)

    # 가드: 후보에 없는 URL(날조)은 폐기
    candidate_urls = {c["url"] for c in candidates}
    result["picks"] = [p for p in result["picks"] if p["url"] in candidate_urls]
    return result


def rank_only(candidates: list[dict]) -> dict:
    """--no-llm: Fable 없이 반응순 상위만 뽑아 자리표시 요약으로 출력."""
    picks = []
    per_platform: dict[str, int] = {}
    for c in candidates:
        n = per_platform.get(c["platform"], 0)
        if n >= PARAMS["picks_per_platform"]:
            continue
        per_platform[c["platform"]] = n + 1
        picks.append({
            "platform": c["platform"],
            "url": c["url"],
            "level": "🔧",
            "title_ko": f"@{c['author']} 게시물",
            "summary_ko": c["text"][:120],
            "why_important_ko": "(--no-llm 모드: 요약 생략)",
        })
    return {"picks": picks, "career_signal_ko": "(--no-llm 모드: 시그널 생략)"}


# ---------------------------------------------------------------------------
# 4) 렌더링
# ---------------------------------------------------------------------------
PLATFORM_LABEL = {
    "youtube": "📺 유튜브",
    "tiktok": "🎵 틱톡",
    "instagram": "📸 인스타그램",
    "threads": "🧵 Threads",
    "twitter": "🐦 X(트위터)",
}


def render_markdown(result: dict) -> str:
    lines = ["## 📡 SNS 화제 (유튜브 · 틱톡 · 인스타 · Threads · X)", "",
             "> Apify 수집 + Fable 5 선별 (최근 2주 · 반응 상위 · 직접 링크만)", ""]
    for p in result["picks"]:
        lines += [
            f"### {p['level']} {PLATFORM_LABEL[p['platform']]} — {p['title_ko']}",
            f"> TL;DR: {p['summary_ko']}",
            "",
            f"**왜 중요:** {p['why_important_ko']}",
            f"[🔗 보기]({p['url']})",
            "",
        ]
    lines += ["### 💼 커리어 시그널", "", result["career_signal_ko"], ""]
    return "\n".join(lines)


def render_kakao(result: dict) -> str:
    lines = ["【SNS】📡 유튜브·틱톡·인스타·Threads·X 화제", ""]
    for p in result["picks"]:
        lines += [
            f"{p['level']} {PLATFORM_LABEL[p['platform']]} — {p['title_ko']}",
            f"- {p['summary_ko']}",
            f"👉 {p['why_important_ko']}",
            p["url"],
            "",
        ]
    lines += ["💼 커리어 시그널", result["career_signal_ko"]]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 픽스처 (--dry-run)
# ---------------------------------------------------------------------------
def fixtures() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {"platform": "youtube", "url": "https://www.youtube.com/watch?v=FIXTURE01",
         "author": "devtuber", "text": "Claude Code 서브에이전트 실전 튜토리얼",
         "published_at": (now - timedelta(days=4)).isoformat(), "views": 220000, "likes": 8000, "reposts": 0},
        {"platform": "tiktok", "url": "https://www.tiktok.com/@dev/video/7000000001",
         "author": "airecap", "text": "GPT-5.6 나온 거 30초 정리 #ai",
         "published_at": (now - timedelta(days=1)).isoformat(), "views": 480000, "likes": 30000, "reposts": 900},
        {"platform": "threads", "url": "https://www.threads.com/@dev/post/AAA",
         "author": "dev", "text": "GPT-5.6 Sol로 agent 파이프라인 재구축한 후기",
         "published_at": (now - timedelta(days=2)).isoformat(), "views": 52000, "likes": 900, "reposts": 120},
        {"platform": "twitter", "url": "https://x.com/dev/status/111",
         "author": "dev2", "text": "Claude Code 서브에이전트로 코드리뷰 자동화하는 법 🧵",
         "published_at": (now - timedelta(days=5)).isoformat(), "views": None, "likes": 800, "reposts": 300},
        {"platform": "twitter", "url": "https://x.com/dev/status/222",
         "author": "dev3", "text": "오래된 글이라 걸러져야 함 ai",
         "published_at": (now - timedelta(days=40)).isoformat(), "views": 99000, "likes": 500, "reposts": 10},
        {"platform": "instagram", "url": "https://www.instagram.com/p/BBB/",
         "author": "coder", "text": "개발자 AI 툴 5가지 릴스",
         "published_at": (now - timedelta(days=1)).isoformat(), "views": 150000, "likes": 4000, "reposts": 0},
        {"platform": "instagram", "url": "https://www.instagram.com/p/CCC/",
         "author": "lowreach", "text": "ai 관련이지만 반응이 적어 걸러져야 함",
         "published_at": (now - timedelta(days=3)).isoformat(), "views": 300, "likes": 5, "reposts": 0},
    ]


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Apify 대신 픽스처 사용")
    ap.add_argument("--no-llm", action="store_true", help="Fable 5 생략(필터·렌더만 테스트)")
    ap.add_argument("--out-dir", default="out", help="결과 저장 디렉토리")
    ap.add_argument("--platforms", default=",".join(ACTORS),
                    help=f"수집할 플랫폼 (콤마 구분, 기본: 전체 = {','.join(ACTORS)})")
    args = ap.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    unknown = [p for p in platforms if p not in ACTORS]
    if unknown:
        sys.exit(f"알 수 없는 플랫폼: {unknown} (지원: {list(ACTORS)})")

    items = fixtures() if args.dry_run else collect_from_apify(platforms)
    if args.dry_run:
        items = [i for i in items if i["platform"] in platforms]
    print(f"[filter] 수집 {len(items)}건", file=sys.stderr)
    candidates = apply_filters(items)
    print(f"[filter] 파라미터 통과 {len(candidates)}건 "
          f"(최근 {PARAMS['recency_days']}일 · views≥{PARAMS['min_views']} 또는 반응≥{PARAMS['min_engagement']})",
          file=sys.stderr)
    if not candidates:
        sys.exit("후보가 없습니다 — 파라미터를 완화하거나 검색어를 조정하세요.")

    result = rank_only(candidates) if args.no_llm else curate_with_fable(candidates)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    md_path = out / f"{today}-sns.md"
    kakao_path = out / f"{today}-sns-kakao.txt"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    kakao_path.write_text(render_kakao(result), encoding="utf-8")
    print(f"[done] {md_path}\n[done] {kakao_path}")


if __name__ == "__main__":
    main()
