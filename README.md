# korjobs — IT · AI 뉴스 큐레이션

중급(intermediate~moderate) 개발자를 위한 IT·AI 뉴스 다이제스트.
입문용 콘텐츠를 섞어 흥미를 유지하고, **뉴스 + 영상 + Threads**를 조회수/화제성 기준으로 정리합니다.
결과물은 **카카오톡으로 뿌리기 좋은 플레인 텍스트**와 **GitHub 상세 아카이브** 두 가지로 만듭니다.

## 구성

| 경로 | 설명 |
|------|------|
| `broadcast/YYYY-MM-DD-kakao.txt` | 📱 **카톡 배포용** 플레인 텍스트 (실제 뿌릴 것, 6블록 분할) |
| `digests/YYYY-MM-DD.md` | GitHub 상세 아카이브 (TL;DR + 접이식 상세) |
| `digests/README.md` | 📚 회차 아카이브 인덱스 |
| `glossary.md` | 📖 공용 용어집 (반복 용어 정의) |
| `templates/digest-template.md` | GitHub 마크다운 템플릿 |
| `templates/kakao-broadcast-template.txt` | 카톡 플레인 텍스트 템플릿 |
| `.claude/commands/*.md` | 🧩 파이프라인 컴포넌트(슬래시 커맨드) — 팀원별 담당 |
| `data/<날짜>/*.json` | 컴포넌트 간 공유 데이터 계약 (상세: [data/SCHEMA.md](data/SCHEMA.md)) |
| `broadcast/YYYY-MM-DD-discord.json` | 🎮 **디스코드 배포용** Embed 페이로드 (승인 봇이 발송) |
| `templates/discord-broadcast-template.md` | 디스코드 Embed 규칙 + JSON 스켈레톤 |
| `bot/send_discord.py` | 🤖 디스코드 승인·발송 봇 (Python) |
| `.env.example` | 봇 토큰/채널 ID 설정 안내 (복사해서 `.env` 작성) |

## 🧩 컴포넌트 기반 워크플로 (팀 병렬 작업용)

다이제스트 제작 과정을 6개의 독립 컴포넌트(슬래시 커맨드)로 나눴습니다. 각자 자기 컴포넌트 파일 하나(`.claude/commands/<이름>.md`)만 브랜치에서 수정하고, 산출물도 자기 담당 파일에만 씁니다 — 그래서 서로 다른 브랜치에서 동시에 작업해도 머지 충돌이 거의 없습니다.

| 컴포넌트 | 담당 파일 | 입력 | 출력 |
|---------|-----------|------|------|
| `/curate-news` | `.claude/commands/curate-news.md` | — | `data/<날짜>/news.json` |
| `/curate-videos` | `.claude/commands/curate-videos.md` | — | `data/<날짜>/videos.json` |
| `/curate-threads` | `.claude/commands/curate-threads.md` | — | `data/<날짜>/threads.json` |
| `/career-signal` | `.claude/commands/career-signal.md` | `news.json` (읽기) | `data/<날짜>/career.json` |
| `/assemble-digest` | `.claude/commands/assemble-digest.md` | 위 4개 JSON (읽기) | `digests/<날짜>.md`, `digests/README.md` |
| `/format-kakao` | `.claude/commands/format-kakao.md` | 위 4개 JSON (읽기) | `broadcast/<날짜>-kakao.txt` |
| `/format-discord` | `.claude/commands/format-discord.md` | 위 4개 JSON (읽기) | `broadcast/<날짜>-discord.json` |

**규칙**
- 각 컴포넌트는 **자기 출력 파일만** 쓰고, 다른 컴포넌트의 산출물은 읽기만 합니다.
- 컴포넌트 간 계약은 [data/SCHEMA.md](data/SCHEMA.md)에 JSON 스키마로 고정되어 있습니다. 스키마를 바꾸려면 팀 전체와 논의 후 변경하세요(다른 컴포넌트가 깨질 수 있음).
- 브랜치 네이밍 예: `feature/curate-news`, `feature/curate-videos` — 자기 담당 `.md` 파일만 수정 후 main에 머지.
- `assemble-digest`와 `format-kakao`, `format-discord`는 서로 의존하지 않고 셋 다 `data/` JSON만 읽으므로 병렬 실행 가능합니다.
- 디스코드 발송은 슬래시 커맨드가 아닌 **Python 실행 단계**입니다: `python bot/send_discord.py <날짜>` (아래 섹션 참고).

## 📤 디스코드 배포 (승인 → 발송)

```
/format-discord <날짜>                    → broadcast/<날짜>-discord.json (status: draft)
python bot/send_discord.py <날짜>         → 승인 채널에 미리보기 6개 + 버튼
  ├─ ✅ 승인 후 발송  → 공지 채널로 발송, status: sent 기록 → git 커밋
  ├─ ✏️ 편집         → 섹션 선택 → 모달에서 제목/내용 수정 → 미리보기·파일 즉시 반영 (여러 번 가능)
  └─ ❌ 반려         → status: rejected 기록, 발송 안 함
```

- 발송된 내용(편집 포함)은 `broadcast/<날짜>-discord.json`에 그대로 저장되므로, 발송 후 커밋하면 **실제 나간 내용이 git에 남습니다** (`edit_log`에 누가 언제 수정했는지 포함).
- 승인 권한: 기본은 승인 채널 멤버 전원(채널을 비공개로 유지하세요). `.env`의 `APPROVER_IDS`에 유저 ID를 넣으면 그 사람들만 버튼을 누를 수 있습니다.

### 봇 설정 (최초 1회)

1. [Discord 개발자 포털](https://discord.com/developers/applications) → **New Application** → Bot 탭 → **Reset Token**으로 토큰 복사
   - Privileged Gateway Intents 3개는 **모두 OFF 유지** (이 봇은 필요 없음)
2. OAuth2 → URL Generator → scope **bot** → 권한 **View Channels, Send Messages, Embed Links** → 생성된 URL로 서버에 초대
3. 서버에 비공개 `#승인` 채널과 공개 `#공지` 채널 준비, 봇에게 두 채널 열람/쓰기 권한 부여
4. 디스코드 설정에서 **개발자 모드** 켜고 채널 우클릭 → ID 복사
5. 로컬 세팅:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r bot/requirements.txt
   copy .env.example .env    ← 열어서 토큰/채널 ID 채우기
   ```

### 재발송·반려·시간초과 규칙

| 상황 | 동작 |
|------|------|
| 이미 `status: sent`인 회차 재실행 | 거부됨 — 재발송하려면 `--force` |
| `--dry-run` | 디스코드 연결 없이 글자수/한도 검증 리포트만 출력 |
| 승인 시간 초과 (기본 3600초, `--timeout N`으로 조정) | 아무것도 발송 안 함, status는 `draft` 유지 — 재실행하면 됨 |
| 반려 후 다시 보내고 싶을 때 | 파일 수정(또는 `/format-discord` 재실행) 후 스크립트 재실행 |

## 선정 원칙
- 📈 **화제성/실용성 우선** — 영상은 실습·튜토리얼 위주(뉴스요약은 최소), 뉴스는 화제성 순
- 🎬 **실제 영상 링크만** — 영상은 반드시 실제 영상 watch URL(`youtube.com/watch?v=...`). 채널 홈·집계 사이트·재생목록 링크 금지
- 🔗 **뉴스도 직접 링크만** — 개별 기사 본문 또는 공식 발표(회사 블로그·정부 발표) URL만. 언론사 홈·뉴스 모음/집계 페이지 링크 금지
- 🗓 **최근 2주 영상만** — 최신 토픽(Sonnet 5·Claude Code 등)을 다루는 실습/튜토리얼 위주. 게시일 확인 불가 시 **"추정 게시일" 표기 + 배포 전 본인 확인**
- 🎯 **레벨 믹스** — 🌱 입문 / 🔧 중급 / 🚀 심화를 골고루
- 🧵 **Threads 항상 포함** — 개발자 커뮤니티 화제 스레드
- 💼 **커리어·채용 시그널** — 뉴스가 한국 개발자 채용·스킬에 주는 의미
- 🛠 **실무 적용성** — "그래서 내 코드/커리어에 뭐가 바뀌나"

## 새 회차 만들기
1. **GitHub판:** `templates/digest-template.md` 복사 → `digests/<오늘 날짜>.md` 채우기
2. **카톡판:** `templates/kakao-broadcast-template.txt` 복사 → `broadcast/<오늘 날짜>-kakao.txt`
   - ⚠️ 카톡은 마크다운 미지원 → 표·`[]()`·`<details>` 금지, **전체 URL** 사용, 6블록 분할
3. **디스코드판:** `/format-discord <오늘 날짜>` → `python bot/send_discord.py <오늘 날짜>` → 승인 채널에서 ✅ (위 "디스코드 배포" 섹션)
4. `digests/README.md` 인덱스 맨 위에 한 줄 추가

### 최근 회차
- [2026-07-08](digests/2026-07-08.md) · [카톡판](broadcast/2026-07-08-kakao.txt)
