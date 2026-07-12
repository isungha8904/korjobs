#!/usr/bin/env python3
"""korjobs 디스코드 승인·발송 봇.

broadcast/<date>-discord.json 을 읽어 승인 채널에 미리보기를 올리고,
✅승인 / ✏️편집 / 🚫섹션 제외 / 📨발송 채널(라우팅) / ❌반려 버튼 인터랙션을 처리한 뒤
승인 시 섹션별 대상 채널(bot/routes.json + 즉석 변경, 기본은 공지 채널)로 발송한다.
상주 봇이 아니라 실행 → 승인 대기 → 발송 → 종료하는 1회성 스크립트.

사용법:
    python bot/send_discord.py 2026-07-12
    python bot/send_discord.py 2026-07-12 --dry-run          # 네트워크 없이 검증만
    python bot/send_discord.py 2026-07-12 --force            # 이미 발송된 회차 재발송
    python bot/send_discord.py 2026-07-12 --timeout 120      # 승인 대기 초 (기본 86400 = 24시간)

종료 코드: 0=발송 완료(또는 dry-run 통과) · 1=반려/입력 오류 · 2=승인 시간 초과 · 3=실행 중 예외
"""

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SECTION_ORDER = ["top3", "news", "videos", "threads", "career", "glossary"]
TITLE_LIMIT = 256
DESC_HARD_LIMIT = 4000   # 편집 모달 TextInput 최대치 — 이 이상이면 모달 프리필이 깨진다
DESC_SOFT_LIMIT = 3800   # 계약상 권장 한도 (SCHEMA.md)
CONTENT_LIMIT = 2000
FOOTER_LIMIT = 2048
EMBED_TOTAL_LIMIT = 6000  # 디스코드 임베드 합산(제목+본문+footer 등) 한도


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fmt_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}시간")
    if m:
        parts.append(f"{m}분")
    if s and not h:
        parts.append(f"{s}초")
    return " ".join(parts) or "0초"


def fail(msg: str, code: int = 1):
    print(f"오류: {msg}")
    sys.exit(code)


def load_payload(date: str):
    path = REPO_ROOT / "broadcast" / f"{date}-discord.json"
    if not path.exists():
        fail(f"{path.relative_to(REPO_ROOT)} 이 없습니다. /format-discord {date} 를 먼저 실행하세요.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{path.name} JSON 파싱 실패: {e}")
    return path, payload


def save_payload(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


ROUTES_PATH = REPO_ROOT / "bot" / "routes.json"


def load_routes():
    """bot/routes.json → (routes: dict[key, list[int]], errors, warnings). 파일 없으면 전부 기본 채널."""
    errors, warnings = [], []
    if not ROUTES_PATH.exists():
        return {}, errors, warnings
    try:
        raw = json.loads(ROUTES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {}, [f"bot/routes.json 파싱 실패: {e}"], warnings
    if not isinstance(raw, dict):
        return {}, ["bot/routes.json 최상위는 객체(섹션 key → 채널 ID 목록)여야 합니다"], warnings
    routes = {}
    for key, value in raw.items():
        if key not in SECTION_ORDER:
            errors.append(f"bot/routes.json: 알 수 없는 섹션 key '{key}' (가능: {', '.join(SECTION_ORDER)})")
            continue
        if not isinstance(value, list):
            errors.append(f"bot/routes.json: '{key}' 값은 채널 ID 목록이어야 합니다")
            continue
        if not value:
            errors.append(f"bot/routes.json: '{key}' 가 빈 목록 — 섹션을 기본 채널로 보내려면 키를 삭제하세요")
            continue
        ids = []
        for item in value:
            s = str(item)
            if not s.isdigit():
                errors.append(f"bot/routes.json: '{key}' 의 채널 ID '{item}' 는 숫자여야 합니다")
            elif int(s) in ids:
                warnings.append(f"bot/routes.json: '{key}' 에 중복 채널 ID {s} — 한 번만 발송합니다")
            else:
                ids.append(int(s))
        if ids:
            routes[key] = ids
    return routes, errors, warnings


def validate(payload: dict):
    """(errors, warnings, report_lines) 반환. errors 가 있으면 발송 불가."""
    errors, warnings, report = [], [], []
    msgs = payload.get("messages", [])
    keys = [m.get("key") for m in msgs]
    if keys != SECTION_ORDER:
        errors.append(f"messages 의 key 가 {SECTION_ORDER} 순서와 다릅니다: {keys}")
    if payload.get("status") not in ("draft", "sent", "rejected"):
        errors.append(f"status 값이 잘못됨: {payload.get('status')!r}")
    for m in msgs:
        key = m.get("key", "?")
        embed = m.get("embed") or {}
        title = embed.get("title") or ""
        desc = embed.get("description") or ""
        content = m.get("content") or ""
        footer = embed.get("footer") or ""
        report.append(f"  [{key:8s}] 제목 {len(title):3d}/{TITLE_LIMIT} · 본문 {len(desc):4d}/{DESC_SOFT_LIMIT}"
                      + (f" · 헤더 {len(content)}/{CONTENT_LIMIT}" if content else "")
                      + (" · 🚫 발송 제외" if m.get("excluded") else ""))
        if not title:
            errors.append(f"[{key}] embed.title 이 비어 있음")
        if len(title) > TITLE_LIMIT:
            errors.append(f"[{key}] 제목 {len(title)}자 — 한도 {TITLE_LIMIT}자 초과")
        if not desc:
            errors.append(f"[{key}] embed.description 이 비어 있음")
        if len(desc) > DESC_HARD_LIMIT:
            errors.append(f"[{key}] 본문 {len(desc)}자 — 편집 모달 한도 {DESC_HARD_LIMIT}자 초과 (섹션 항목을 줄이세요)")
        elif len(desc) > DESC_SOFT_LIMIT:
            warnings.append(f"[{key}] 본문 {len(desc)}자 — 권장 한도 {DESC_SOFT_LIMIT}자 초과 (편집 여유 부족)")
        if len(content) > CONTENT_LIMIT:
            errors.append(f"[{key}] content {len(content)}자 — 한도 {CONTENT_LIMIT}자 초과")
        if len(footer) > FOOTER_LIMIT:
            errors.append(f"[{key}] footer {len(footer)}자 — 한도 {FOOTER_LIMIT}자 초과")
        combined = len(title) + len(desc) + len(footer)
        if combined > EMBED_TOTAL_LIMIT:
            errors.append(f"[{key}] 제목+본문+footer 합계 {combined}자 — 디스코드 임베드 합산 한도 {EMBED_TOTAL_LIMIT}자 초과")
        color = embed.get("color")
        if color is not None and not isinstance(color, int):
            errors.append(f"[{key}] color 는 10진수 정수여야 함: {color!r}")
    if msgs and all(m.get("excluded") for m in msgs):
        errors.append("모든 섹션이 발송 제외 상태입니다 — 최소 1개는 포함해야 합니다")
    return errors, warnings, report


def parse_args():
    p = argparse.ArgumentParser(description="korjobs 디스코드 승인·발송 봇")
    p.add_argument("date", help="발송할 회차 날짜 (YYYY-MM-DD)")
    p.add_argument("--dry-run", action="store_true", help="디스코드 연결 없이 검증 리포트만 출력")
    p.add_argument("--force", action="store_true", help="status=sent 인 회차도 재발송 허용")
    p.add_argument("--timeout", type=int, default=86400, help="승인 대기 시간(초), 기본 86400(24시간)")
    return p.parse_args()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = parse_args()
    path, payload = load_payload(args.date)
    if not isinstance(payload.get("edit_log"), list):
        payload["edit_log"] = []  # 봇이 기록하는 필드 — 없거나 깨져 있으면 초기화

    errors, warnings, report = validate(payload)
    standing_routes, r_errors, r_warnings = load_routes()
    errors += r_errors
    warnings += r_warnings
    print(f"── {args.date} 디스코드 배포판 검증 ──")
    print("\n".join(report))
    print("── 발송 채널 라우팅 (bot/routes.json) ──")
    for key in SECTION_ORDER:
        # dry-run 은 .env 를 읽지 않으므로 기본 채널은 상징 라벨로 표기
        targets = standing_routes.get(key)
        label = " ".join(f"<#{c}>" for c in targets) if targets else "기본 공지 채널 (ANNOUNCE_CHANNEL_ID)"
        print(f"  [{key:8s}] {label}")
    for w in warnings:
        print(f"경고: {w}")
    if errors:
        for e in errors:
            print(f"오류: {e}")
        sys.exit(1)

    if args.dry_run:
        if payload.get("status") == "sent":
            print(f"참고: 이미 {payload.get('sent_at')} 에 발송된 회차입니다. (실제 재발송은 --force 필요)")
        print("dry-run 통과 ✅ — 디스코드에 연결하지 않았습니다.")
        sys.exit(0)

    if payload.get("status") == "sent" and not args.force:
        fail(f"이미 {payload.get('sent_at')} 에 발송된 회차입니다. 재발송하려면 --force 를 붙이세요.")

    # 여기서부터만 discord/dotenv 의존 (dry-run 은 의존성 설치 없이도 동작)
    import discord  # noqa: E402
    from dotenv import load_dotenv  # noqa: E402
    import os

    load_dotenv(REPO_ROOT / ".env")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    approval_id = os.getenv("APPROVAL_CHANNEL_ID", "").strip()
    announce_id = os.getenv("ANNOUNCE_CHANNEL_ID", "").strip()
    approver_raw = os.getenv("APPROVER_IDS", "").strip()

    if not token or not approval_id or not announce_id:
        fail(".env 에 DISCORD_BOT_TOKEN / APPROVAL_CHANNEL_ID / ANNOUNCE_CHANNEL_ID 를 채우세요. (.env.example 참고)")
    try:
        approval_id, announce_id = int(approval_id), int(announce_id)
    except ValueError:
        fail("채널 ID 는 숫자여야 합니다. 디스코드 개발자 모드를 켜고 채널 우클릭 > ID 복사.")
    try:
        approver_ids = {int(x) for x in approver_raw.split(",") if x.strip()}
    except ValueError:
        fail("APPROVER_IDS 는 콤마로 구분한 숫자 유저 ID 여야 합니다.")

    # ── 이하 디스코드 상호작용 ──────────────────────────────────────────

    class State:
        def __init__(self):
            self.payload = payload
            self.path = path
            self.preview_msgs = {}       # key -> discord.Message (승인 채널 미리보기)
            self.locked = False          # 승인/반려 후 편집 차단
            self.approve_interaction = None
            self.route_overrides = {}    # key -> [채널ID int] — 이번 실행에만 적용, routes.json 은 안 건드림

        def message_by_key(self, key: str) -> dict:
            return next(m for m in self.payload["messages"] if m["key"] == key)

        def targets_for(self, key: str) -> list:
            if key in self.route_overrides:
                return self.route_overrides[key]
            return standing_routes.get(key) or [announce_id]

    def preview_content(m: dict, targets: list):
        """승인 채널 미리보기용 content — 제외 마커와 (기본값이 아닐 때만) 발송 대상 채널을 표시."""
        lines = []
        if m.get("excluded"):
            lines.append("🚫 **이 섹션은 발송에서 제외됩니다**")
        if targets != [announce_id]:
            lines.append("📨 **발송 대상:** " + " ".join(f"<#{c}>" for c in targets))
        base = m.get("content")
        if lines:
            return "\n".join(lines + ([base] if base else []))
        return base

    def build_embed(m: dict) -> discord.Embed:
        e = m["embed"]
        embed = discord.Embed(
            title=e.get("title"),
            description=e.get("description"),
            url=e.get("url") or None,
            color=e.get("color"),
        )
        if e.get("footer"):
            embed.set_footer(text=e["footer"])
        return embed

    class SectionEditModal(discord.ui.Modal):
        def __init__(self, state: State, key: str):
            m = state.message_by_key(key)
            super().__init__(title=f"✏️ {m['embed']['title']}"[:45])
            self.state, self.key = state, key
            self.title_input = discord.ui.TextInput(
                label="제목", style=discord.TextStyle.short,
                default=m["embed"]["title"], max_length=TITLE_LIMIT)
            self.desc_input = discord.ui.TextInput(
                label="내용 (마크다운 가능)", style=discord.TextStyle.paragraph,
                default=m["embed"]["description"], max_length=DESC_HARD_LIMIT)
            self.add_item(self.title_input)
            self.add_item(self.desc_input)
            self.content_input = None
            if "content" in m:  # 값을 비워도 키는 남으므로, 실수로 지운 헤더를 다시 복구할 수 있다
                self.content_input = discord.ui.TextInput(
                    label="브리핑 헤더 (카드 위에 뜨는 첫 줄)", style=discord.TextStyle.paragraph,
                    default=m.get("content") or "", max_length=CONTENT_LIMIT, required=False)
                self.add_item(self.content_input)

        async def on_submit(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 반영할 수 없습니다.", ephemeral=True)
                return
            m = self.state.message_by_key(self.key)
            new_content = (self.content_input.value or None) if self.content_input is not None else m.get("content")
            candidate = {**m, "content": new_content,
                         "embed": {**m["embed"],
                                   "title": self.title_input.value,
                                   "description": self.desc_input.value}}
            # 미리보기 반영이 성공한 경우에만 payload 에 커밋 — 미리보기와 발송 내용이 항상 일치하도록
            await self.state.preview_msgs[self.key].edit(
                content=preview_content(candidate, self.state.targets_for(self.key)), embed=build_embed(candidate))
            m["embed"]["title"] = candidate["embed"]["title"]
            m["embed"]["description"] = candidate["embed"]["description"]
            if self.content_input is not None:
                m["content"] = new_content
            self.state.payload["edit_log"].append({
                "key": self.key,
                "editor": interaction.user.display_name,
                "edited_at": now_iso(),
            })
            save_payload(self.state.path, self.state.payload)
            await interaction.response.send_message(
                f"✅ '{m['embed']['title']}' 섹션 수정 완료 — 미리보기와 파일에 반영했습니다.", ephemeral=True)

    class HeaderEditModal(discord.ui.Modal):
        """맨 위 브리핑 헤더(top3 카드 위 일반 텍스트 첫 줄)만 빠르게 수정하는 모달."""

        def __init__(self, state: State):
            super().__init__(title="✏️ 브리핑 헤더 수정")
            self.state = state
            m = state.message_by_key("top3")
            self.header_input = discord.ui.TextInput(
                label="브리핑 헤더 (맨 위 첫 줄)", style=discord.TextStyle.paragraph,
                default=m.get("content") or "", max_length=CONTENT_LIMIT, required=False)
            self.add_item(self.header_input)

        async def on_submit(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 반영할 수 없습니다.", ephemeral=True)
                return
            m = self.state.message_by_key("top3")
            candidate = {**m, "content": self.header_input.value or None}
            await self.state.preview_msgs["top3"].edit(
                content=preview_content(candidate, self.state.targets_for("top3")), embed=build_embed(candidate))
            m["content"] = candidate["content"]
            self.state.payload["edit_log"].append({
                "key": "top3",
                "editor": interaction.user.display_name,
                "edited_at": now_iso(),
                "action": "edit-header",
            })
            save_payload(self.state.path, self.state.payload)
            await interaction.response.send_message("✅ 브리핑 헤더 수정 완료 — 미리보기에 반영했습니다.", ephemeral=True)

    HEADER_OPTION = "_header"

    class SectionSelect(discord.ui.Select):
        def __init__(self, state: State):
            self.state = state
            options = [discord.SelectOption(
                label="🗞️ 브리핑 헤더 (맨 위 첫 줄)", value=HEADER_OPTION,
                description="IT·AI 뉴스 브리핑 · 날짜 · 대상 독자 줄")]
            options += [discord.SelectOption(label=state.message_by_key(k)["embed"]["title"][:100], value=k)
                        for k in SECTION_ORDER]
            super().__init__(placeholder="수정할 항목 선택", options=options)

        async def callback(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 편집할 수 없습니다.", ephemeral=True)
                return
            if self.values[0] == HEADER_OPTION:
                await interaction.response.send_modal(HeaderEditModal(self.state))
            else:
                await interaction.response.send_modal(SectionEditModal(self.state, self.values[0]))

    class SectionPickView(discord.ui.View):
        def __init__(self, state: State):
            super().__init__(timeout=600)
            self.add_item(SectionSelect(state))

    class SectionToggleSelect(discord.ui.Select):
        def __init__(self, state: State):
            self.state = state
            options = [
                discord.SelectOption(
                    label=state.message_by_key(k)["embed"]["title"][:100], value=k,
                    default=not state.message_by_key(k).get("excluded"),
                    description="현재: 발송 제외" if state.message_by_key(k).get("excluded") else "현재: 발송",
                )
                for k in SECTION_ORDER
            ]
            super().__init__(placeholder="발송할 섹션만 선택 (선택 해제 = 제외)",
                             options=options, min_values=1, max_values=len(SECTION_ORDER))

        async def callback(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 변경할 수 없습니다.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)  # 미리보기 여러 개 수정에 3초 이상 걸릴 수 있음
            included = set(self.values)
            changed = []
            for m in self.state.payload["messages"]:
                new_excluded = m["key"] not in included
                if bool(m.get("excluded")) != new_excluded:
                    m["excluded"] = new_excluded
                    changed.append((m["key"], new_excluded))
            for key, _ in changed:
                m = self.state.message_by_key(key)
                await self.state.preview_msgs[key].edit(
                    content=preview_content(m, self.state.targets_for(key)), embed=build_embed(m))
            for key, excluded in changed:
                self.state.payload["edit_log"].append({
                    "key": key,
                    "editor": interaction.user.display_name,
                    "edited_at": now_iso(),
                    "action": "exclude" if excluded else "include",
                })
            if changed:
                save_payload(self.state.path, self.state.payload)
            n = sum(1 for m in self.state.payload["messages"] if not m.get("excluded"))
            await interaction.followup.send(
                f"✅ 발송 대상 갱신 — {n}/{len(SECTION_ORDER)}개 섹션 발송 예정", ephemeral=True)

    class SectionToggleView(discord.ui.View):
        def __init__(self, state: State):
            super().__init__(timeout=600)
            self.add_item(SectionToggleSelect(state))

    class RouteChannelSelect(discord.ui.ChannelSelect):
        def __init__(self, state: State, key: str, default_ids: list):
            self.state, self.key = state, key
            super().__init__(
                channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                placeholder="발송할 채널 선택 (모두 해제 = 기본값 복원)",
                min_values=0, max_values=25,
                default_values=[discord.Object(id=c) for c in default_ids])

        async def callback(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 변경할 수 없습니다.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)  # 권한 검사 + 미리보기 수정 + 저장에 3초 이상 걸릴 수 있음
            # self.values 는 AppCommandChannel — Messageable 이 아니므로 .id 만 쓰고 발송 시 재해석
            picked = [c.id for c in self.values]
            # 선택 목록은 '사용자가 보는 채널' 기준이라 봇이 못 쓰는 채널이 섞일 수 있음 → 즉시 검사
            bad = []
            for cid in picked:
                ch = interaction.client.get_channel(cid)
                if ch is None or not ch.permissions_for(ch.guild.me).send_messages:
                    bad.append(cid)
            if bad:
                await interaction.followup.send(
                    "⚠️ 봇이 접근/발송할 수 없는 채널이 있어 반영하지 않았습니다: "
                    + " ".join(f"<#{c}>" for c in bad)
                    + "\n채널 권한에 봇을 추가한 뒤 다시 시도하세요.", ephemeral=True)
                return
            if picked:
                self.state.route_overrides[self.key] = picked
            else:
                self.state.route_overrides.pop(self.key, None)  # 전부 해제 = 기본값 복원
            m = self.state.message_by_key(self.key)
            targets = self.state.targets_for(self.key)
            await self.state.preview_msgs[self.key].edit(
                content=preview_content(m, targets), embed=build_embed(m))
            self.state.payload["edit_log"].append({
                "key": self.key,
                "editor": interaction.user.display_name,
                "edited_at": now_iso(),
                "action": "route",
                "channels": [str(c) for c in targets],
            })
            save_payload(self.state.path, self.state.payload)
            label = " ".join(f"<#{c}>" for c in picked) if picked else "기본값 복원 (공지 채널)"
            await interaction.followup.send(
                f"📨 '{m['embed']['title']}' 발송 대상 → {label}", ephemeral=True)

    class RouteChannelView(discord.ui.View):
        def __init__(self, state: State, key: str, default_ids: list):
            super().__init__(timeout=600)
            self.add_item(RouteChannelSelect(state, key, default_ids))

    class RouteSectionSelect(discord.ui.Select):
        def __init__(self, state: State):
            self.state = state
            options = []
            for k in SECTION_ORDER:
                targets = state.targets_for(k)
                desc = "현재: 기본 공지 채널" if targets == [announce_id] else f"현재: {len(targets)}개 채널 지정"
                options.append(discord.SelectOption(
                    label=state.message_by_key(k)["embed"]["title"][:100], value=k, description=desc))
            super().__init__(placeholder="발송 채널을 바꿀 섹션 선택", options=options)

        async def callback(self, interaction: discord.Interaction):
            if self.state.locked:
                await interaction.response.send_message("이미 승인/반려되어 변경할 수 없습니다.", ephemeral=True)
                return
            key = self.values[0]
            # default_values 에 길드에 없는 채널 ID 가 섞이면 400 에러 → 캐시로 확인되는 것만 프리필
            default_ids = [c for c in self.state.targets_for(key)
                           if interaction.client.get_channel(c) is not None]
            title = self.state.message_by_key(key)["embed"]["title"]
            await interaction.response.edit_message(
                content=f"📨 '{title}' 섹션의 발송 채널을 선택하세요 (모두 해제 = 기본값 복원):",
                view=RouteChannelView(self.state, key, default_ids))

    class RoutePickView(discord.ui.View):
        def __init__(self, state: State):
            super().__init__(timeout=600)
            self.add_item(RouteSectionSelect(state))

    class ApprovalView(discord.ui.View):
        def __init__(self, state: State, timeout: float):
            super().__init__(timeout=timeout)
            self.state = state
            self.result = None
            self.actor = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if approver_ids and interaction.user.id not in approver_ids:
                await interaction.response.send_message("승인 권한이 없습니다.", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="승인 후 발송", emoji="✅", style=discord.ButtonStyle.success)
        async def approve(self, interaction: discord.Interaction, _button: discord.ui.Button):
            if self.state.locked:  # 동시 클릭 시 먼저 처리된 결정을 유지
                await interaction.response.send_message("이미 처리된 요청입니다.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)  # 발송에 3초 이상 걸리므로 먼저 ack
            self.state.locked = True
            self.state.approve_interaction = interaction
            self.result, self.actor = "approved", interaction.user.display_name
            self.stop()

        @discord.ui.button(label="편집", emoji="✏️", style=discord.ButtonStyle.primary)
        async def edit(self, interaction: discord.Interaction, _button: discord.ui.Button):
            if self.state.locked:
                await interaction.response.send_message("이미 처리된 요청입니다.", ephemeral=True)
                return
            await interaction.response.send_message(
                "수정할 섹션을 선택하세요:", view=SectionPickView(self.state), ephemeral=True)

        @discord.ui.button(label="섹션 제외/복원", emoji="🚫", style=discord.ButtonStyle.secondary)
        async def toggle_sections(self, interaction: discord.Interaction, _button: discord.ui.Button):
            if self.state.locked:
                await interaction.response.send_message("이미 처리된 요청입니다.", ephemeral=True)
                return
            await interaction.response.send_message(
                "발송할 섹션만 선택하세요 (선택 해제한 섹션은 발송에서 제외):",
                view=SectionToggleView(self.state), ephemeral=True)

        @discord.ui.button(label="발송 채널", emoji="📨", style=discord.ButtonStyle.secondary)
        async def route_sections(self, interaction: discord.Interaction, _button: discord.ui.Button):
            # row 0 에 버튼 5개 = 디스코드 한도 — 6번째 액션을 추가하려면 row= 지정 필요
            if self.state.locked:
                await interaction.response.send_message("이미 처리된 요청입니다.", ephemeral=True)
                return
            await interaction.response.send_message(
                "발송 채널을 바꿀 섹션을 선택하세요:", view=RoutePickView(self.state), ephemeral=True)

        @discord.ui.button(label="반려", emoji="❌", style=discord.ButtonStyle.danger)
        async def reject(self, interaction: discord.Interaction, _button: discord.ui.Button):
            if self.state.locked:
                await interaction.response.send_message("이미 처리된 요청입니다.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            self.state.locked = True
            self.result, self.actor = "rejected", interaction.user.display_name
            self.stop()

    async def fetch_text_channel(client: discord.Client, channel_id: int, name: str):
        try:
            channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        except discord.NotFound:
            raise RuntimeError(f"{name} 채널({channel_id})을 찾을 수 없습니다. 채널 ID 를 확인하세요.")
        except discord.Forbidden:
            raise RuntimeError(f"{name} 채널({channel_id})에 접근 권한이 없습니다. 봇을 서버에 초대하고 채널 열람 권한을 주세요.")
        if not isinstance(channel, discord.abc.Messageable):
            raise RuntimeError(f"{name} 채널({channel_id})은 메시지를 보낼 수 있는 채널이 아닙니다.")
        return channel

    async def run_flow(client: discord.Client, state: State) -> int:
        approval = await fetch_text_channel(client, approval_id, "승인")
        announce = await fetch_text_channel(client, announce_id, "공지")

        await approval.send(
            f"📋 **{args.date} 다이제스트 승인 요청**\n"
            f"아래 미리보기 {len(SECTION_ORDER)}개 섹션을 확인하고 맨 아래 버튼을 사용하세요:\n"
            f"✅ 승인 후 발송 · ✏️ 편집(제목/내용/헤더) · 🚫 섹션 제외/복원 · 📨 발송 채널 · ❌ 반려\n"
            f"⏰ 대기 시간: {fmt_duration(args.timeout)}")
        for m in state.payload["messages"]:
            msg = await approval.send(content=preview_content(m, state.targets_for(m["key"])), embed=build_embed(m))
            state.preview_msgs[m["key"]] = msg

        view = ApprovalView(state, timeout=args.timeout)
        control = await approval.send("👇 검토 후 선택하세요.", view=view)

        timed_out = await view.wait()
        for child in view.children:
            child.disabled = True

        async def edit_control(text: str):
            # 결과가 이미 확정된 뒤의 부가 작업 — 실패해도 종료 코드를 바꾸지 않는다
            try:
                await control.edit(content=text, view=view)
            except discord.HTTPException as e:
                print(f"경고: 컨트롤 메시지 갱신 실패 (결과에는 영향 없음): {e}")

        if timed_out or view.result is None:
            state.locked = True
            await edit_control("⏰ 승인 시간 초과 — 스크립트를 다시 실행하세요. (status 는 draft 유지)")
            print("승인 시간 초과 — 아무것도 발송하지 않았습니다.")
            return 2

        if view.result == "rejected":
            state.payload["status"] = "rejected"
            save_payload(state.path, state.payload)
            await edit_control(f"❌ 반려됨 — {view.actor}")
            print(f"반려됨 (by {view.actor}) — status=rejected 기록.")
            return 1

        # approved — 제외되지 않은 섹션만, 섹션별 라우팅 대상 채널로 발송
        to_send = [m for m in state.payload["messages"] if not m.get("excluded")]
        skipped = len(state.payload["messages"]) - len(to_send)
        plan = [(m, state.targets_for(m["key"])) for m in to_send]
        total_planned = sum(len(targets) for _, targets in plan)

        # 발송 전 모든 대상 채널을 먼저 해석 — 실패 시 0건 발송 상태로 중단 (멱등성 보존)
        channels = {announce_id: announce}
        try:
            for m, targets in plan:
                for cid in targets:
                    if cid not in channels:
                        channels[cid] = await fetch_text_channel(client, cid, f"[{m['key']}] 라우팅")
        except RuntimeError as e:
            warn = f"⚠️ 발송 중단(발송 전) — {e} (아무것도 발송되지 않음, status 는 draft 유지)"
            await edit_control(warn)
            print(warn)
            return 1

        sent_records = []  # {"key", "channel_id", "message_id"} — ID 는 문자열(2^53 초과 대비)
        try:
            for m, targets in plan:  # 섹션 순서 우선 — 모든 방에서 읽기 순서 보존
                for cid in targets:
                    sent = await channels[cid].send(content=m.get("content"), embed=build_embed(m))
                    sent_records.append({"key": m["key"], "channel_id": str(cid), "message_id": str(sent.id)})
        except discord.HTTPException as e:
            # 부분 발송: 나간 (섹션, 채널) 쌍까지 기록하되 status 는 draft 유지
            state.payload["sent_messages"] = sent_records
            save_payload(state.path, state.payload)
            warn = (f"⚠️ 발송 중단 — [{m['key']}] → <#{cid}> 발송 실패: {e}\n"
                    f"{len(sent_records)}/{total_planned}건 발송됨. 이미 나간 메시지를 정리한 뒤 재실행하세요. "
                    f"(status 는 draft 유지 — 재실행하면 전체가 다시 발송됩니다)")
            await edit_control(warn)
            print(warn)
            return 3
        state.payload["status"] = "sent"
        state.payload["sent_at"] = now_iso()
        state.payload["sent_messages"] = sent_records
        state.payload.pop("announce_message_ids", None)  # 구버전 필드 정리
        save_payload(state.path, state.payload)
        n_channels = len({r["channel_id"] for r in sent_records})
        skipped_note = f" (제외 {skipped}개)" if skipped else ""
        summary = f"{n_channels}개 채널에 {len(sent_records)}개 메시지{skipped_note}"
        await edit_control(f"✅ 발송 완료 — {view.actor} 승인 · {summary}")
        if state.approve_interaction:
            try:
                await state.approve_interaction.followup.send(f"✅ {summary}를 발송했습니다.", ephemeral=True)
            except discord.HTTPException as e:
                print(f"경고: 승인자 확인 메시지 전송 실패 (발송은 완료됨): {e}")
        print(f"발송 완료 (by {view.actor}) — {summary}, status=sent 기록.")
        return 0

    class SenderClient(discord.Client):
        def __init__(self):
            super().__init__(intents=discord.Intents.default())  # 특권 인텐트 불필요
            self.exit_code = 3
            self._started = False

        async def on_ready(self):
            if self._started:   # 재연결 시 on_ready 재발화 방지
                return
            self._started = True
            try:
                self.exit_code = await run_flow(self, State())
            except RuntimeError as e:
                print(f"오류: {e}")
                self.exit_code = 1
            except Exception:
                traceback.print_exc()
                self.exit_code = 3
            finally:
                await self.close()

    client = SenderClient()
    try:
        import logging
        client.run(token, log_level=logging.WARNING)
    except discord.LoginFailure:
        fail("봇 토큰이 잘못되었습니다. 개발자 포털 > Bot > Reset Token 으로 재발급 후 .env 를 갱신하세요.")
    sys.exit(client.exit_code)


if __name__ == "__main__":
    main()
