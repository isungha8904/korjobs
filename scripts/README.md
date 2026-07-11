# 🤖 SNS 자동 큐레이션 (Apify + Claude Fable 5)

Threads · X(트위터) · 인스타그램을 **레포 큐레이션 파라미터**로 수집·필터하고,
**Claude Fable 5**가 선별·한국어 요약·커리어 시그널까지 만들어주는 파이프라인입니다.

## 검색 로직

```
Apify 액터 (플랫폼별 수집)
   ↓  normalize: 액터별 상이한 필드 → 공통 스키마 {url, text, published_at, views, likes, reposts}
파라미터 필터  ←  레포 원칙과 동기화
   · 최근 14일 게시분만 (게시일 파싱 불가 = 배제, 날조 방지)
   · views ≥ 10,000 또는 좋아요+리포스트 ≥ 300
   · 직접 게시물 URL만 · 중복 제거 · AI/개발 키워드 포함
   ↓
Claude Fable 5 (구조화 출력 JSON)
   · 플랫폼당 최대 3개 선별, 레벨(🌱/🔧/🚀) 믹스
   · 용어 풀어쓴 한국어 요약 + "왜 중요" + 커리어 시그널
   · 후보에 없는 URL은 코드에서 폐기 (환각 가드)
   ↓
out/YYYY-MM-DD-sns.md (다이제스트용) + out/YYYY-MM-DD-sns-kakao.txt (카톡 블록)
```

## 설정

```bash
pip install -r scripts/requirements.txt
export APIFY_TOKEN=apify_api_...        # https://console.apify.com/account/integrations
export ANTHROPIC_API_KEY=sk-ant-...     # https://platform.claude.com
```

Apify 액터 ID는 기본값이 들어 있지만, **Apify Store에서 실제 사용할 액터를 확인 후**
환경변수로 교체하는 것을 권장합니다 (액터는 자주 바뀝니다):

```bash
export APIFY_THREADS_ACTOR=curious_coder/threads-scraper
export APIFY_TWITTER_ACTOR=apidojo/tweet-scraper
export APIFY_INSTAGRAM_ACTOR=apify/instagram-scraper
```

## 실행

```bash
python3 scripts/curate_sns.py                # 전체 실행 (Apify + Fable 5)
python3 scripts/curate_sns.py --dry-run      # 내장 픽스처로 파이프라인 검증 (Apify 불필요)
python3 scripts/curate_sns.py --dry-run --no-llm   # 키 없이 필터·렌더 로직만 검증
```

## Fable 5 사용 메모

- `claude-fable-5`는 thinking이 항상 켜져 있어 `thinking` 파라미터를 보내지 않습니다.
- 안전 분류기가 요청을 거절할 수 있어(`stop_reason: refusal`) **서버측 폴백**이 기본 탑재:
  거절 시 같은 호출에서 `claude-opus-4-8`이 이어받습니다 (beta `server-side-fallback-2026-06-01`).
- 출력은 JSON 스키마 강제(`output_config.format`)라 파싱이 항상 안전합니다.
- 30일 데이터 보존이 필요한 모델입니다 — ZDR(무보존) 조직에서는 400이 나며,
  그 경우 `model`을 `claude-opus-4-8`로 바꿔 쓰면 됩니다.

## 파라미터 조정

`scripts/curate_sns.py` 상단 `PARAMS` 딕셔너리에서:

| 키 | 기본값 | 의미 |
|----|--------|------|
| `recency_days` | 14 | 최근 N일 게시분만 |
| `min_views` | 10000 | 조회수 최소치 |
| `min_engagement` | 300 | (조회수 없을 때) 좋아요+리포스트 최소치 |
| `picks_per_platform` | 3 | 플랫폼당 최종 선별 수 |
