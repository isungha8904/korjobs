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
  ├─ ✅ 승인 후 발송  → 제외 안 된 섹션을 각자의 대상 채널로 발송, status: sent 기록 → git 커밋
  ├─ ✏️ 편집         → 섹션 선택 → 모달에서 제목/내용(top3는 브리핑 헤더까지) 수정 → 미리보기·파일 즉시 반영 (여러 번 가능)
  ├─ 🚫 섹션 제외/복원 → 발송할 섹션만 선택 (최소 1개) → 제외 섹션은 미리보기에 🚫 표시, 승인 시 발송 안 됨
  ├─ 📨 발송 채널     → 섹션 선택 → 채널 선택 → 그 섹션만 다른 방(들)으로 발송 (이번 실행 한정, 미리보기에 📨 표시)
  └─ ❌ 반려         → status: rejected 기록, 발송 안 함
```

- 발송된 내용(편집 포함)은 `broadcast/<날짜>-discord.json`에 그대로 저장되므로, 발송 후 커밋하면 **실제 나간 내용이 git에 남습니다** (`edit_log`에 누가 언제 수정했는지 포함, `sent_messages`에 섹션·채널별 발송 기록).
- 승인 권한: 기본은 승인 채널 멤버 전원(채널을 비공개로 유지하세요). `.env`의 `APPROVER_IDS`에 유저 ID를 넣으면 그 사람들만 버튼을 누를 수 있습니다.

### 채널 라우팅 (섹션별 다른 방으로 발송)

기본은 모든 섹션이 `ANNOUNCE_CHANNEL_ID` 한 곳으로 갑니다. 특정 섹션을 다른 방(들)으로 보내려면:

- **영구 규칙**: [bot/routes.json](bot/routes.json)에 섹션 → 채널 ID 목록을 커밋 (형식은 [data/SCHEMA.md](data/SCHEMA.md) 참고). 한 섹션을 여러 채널에 복제 발송할 수 있고, 파일에 없는 섹션은 기본 공지 채널로 갑니다. GitHub Actions 자동 실행에서도 그대로 적용됩니다.
  ```json
  { "career": ["커리어채널ID"], "videos": ["영상채널ID", "공지채널ID"] }
  ```
- **일회성 변경**: 승인 화면의 📨 버튼 — 이번 실행에만 적용되고 routes.json 은 바뀌지 않으며, `edit_log`에 기록됩니다. 승인 시간이 초과되면 일회성 변경은 사라지므로 반복되는 규칙은 routes.json 에 넣으세요.
- 채널 ID는 비밀이 아니라 커밋해도 안전합니다. 단, **대상 채널마다 봇에게 보기/쓰기 권한**을 줘야 합니다 (안 주면 선택 시점과 발송 전에 걸러지고 안내가 뜹니다).
- 📨 선택기에 특정 채널이 안 보이면: 디스코드 채널 선택 목록은 **검색형**이라 채널 이름을 타이핑해 찾을 수 있습니다. 그래도 안 되거나 확실히 하려면 아래 진단 명령으로 봇의 채널 접근 상태를 확인하고, 채널 ID를 routes.json 에 직접 넣으면 됩니다.

### 채널 진단 (선택 안 될 때)

```
python bot/send_discord.py --list-channels
```

봇이 속한 모든 서버의 채널을 **종류(text/news/forum)와 봇 권한(보기·발송·임베드)** 과 함께 채널 ID까지 출력합니다. 특정 채널이 라우팅 선택기에 안 뜰 때, 봇이 그 채널을 볼 수 있는지·발송 권한이 있는지·ID가 무엇인지 바로 확인할 수 있습니다. (발송은 하지 않는 읽기 전용 진단입니다.)

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

### 원격/예약 실행 (GitHub Actions)

로컬 PC 없이도 [.github/workflows/discord-send.yml](.github/workflows/discord-send.yml)로 발송 프로세스를 돌릴 수 있습니다:

- **수동 실행**: GitHub 웹/모바일 앱 → Actions → "Discord 발송 (승인 → 공지)" → **Run workflow** (날짜 비우면 오늘 KST, force 체크 시 재발송)
- **예약 실행**: 매일 05:00 KST 자동 실행 — 단, 그 날짜의 `broadcast/<날짜>-discord.json`이 main에 커밋돼 있을 때만 승인 요청이 올라가고, 없으면 조용히 스킵. 즉 **팀이 `/format-discord` 결과를 커밋해두면 다음날 새벽 자동으로 승인 요청이 뜨는** 흐름
- 승인은 어느 쪽이든 똑같이 디스코드 버튼으로 진행되고, 발송/반려 결과 JSON은 Actions가 자동 커밋
- **최초 1회 설정**: 리포 Settings → Secrets and variables → Actions에 `DISCORD_BOT_TOKEN`, `APPROVAL_CHANNEL_ID`, `ANNOUNCE_CHANNEL_ID` (선택: `APPROVER_IDS`) 등록
- ⚠️ GitHub 러너 작업 한도(6시간) 때문에 원격 실행의 승인 대기는 **최대 5시간**(기본 18000초). 시간 초과되면 다시 트리거하면 됨

### 재발송·반려·시간초과 규칙

| 상황 | 동작 |
|------|------|
| 이미 `status: sent`인 회차 재실행 | 거부됨 — 재발송하려면 `--force` |
| `--dry-run` | 디스코드 연결 없이 글자수/한도 검증 리포트만 출력 |
| 승인 시간 초과 (기본 24시간, `--timeout N`초로 조정) | 아무것도 발송 안 함, status는 `draft` 유지 — 재실행하면 됨. ⚠️ 대기 중에는 스크립트를 실행한 PC가 켜져 있어야 함 |
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
