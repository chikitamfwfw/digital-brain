"""タスク操作ロジック。

GitHub Issue をタスクの実体、Projects v2 ボードをビューとして扱う。
Issue の作成・更新は必ず成功し、Projects v2 への登録・フィールド設定はベスト
エフォート（失敗しても Issue は作成される）。
"""
from __future__ import annotations

from services.github_tasks import GitHubTasks, GitHubError, STATUS_VALUES


class TaskService:
    def __init__(self, vault: object | None = None) -> None:
        self._gh: GitHubTasks | None = None
        self._vault = vault

    @property
    def gh(self) -> GitHubTasks:
        if self._gh is None:
            self._gh = GitHubTasks()
        return self._gh

    # ── ボード操作の補助 ────────────────────────────────────────────────────
    def _find_item_id(self, project: dict, issue_number: int) -> str | None:
        """ボード上の Issue の item ID を返す（無ければ None）。"""
        try:
            for item in self.gh.board_items(project["id"]):
                if item["number"] == issue_number:
                    return item["item_id"]
        except GitHubError:
            pass
        return None

    def _set_board_status(self, issue_number: int, status: str) -> bool:
        """ボード上の Issue の Status を設定する。成功可否を返す。"""
        project = self.gh.ensure_project()
        if not project:
            return False
        option_id = project["status"]["options"].get(status)
        field_id = project["status"]["field_id"]
        if not option_id or not field_id:
            return False
        item_id = self._find_item_id(project, issue_number)
        if not item_id:
            return False
        try:
            self.gh.set_status(project["id"], item_id, field_id, option_id)
            return True
        except GitHubError:
            return False

    def _apply_fields(
        self,
        project: dict,
        item_id: str,
        anken: str | None = None,
        due: str | None = None,
        effort: float | None = None,
        priority: str | None = None,
    ) -> list[str]:
        """ボード項目にカスタムフィールド値を設定する（best-effort）。

        設定できたフィールド名のリストを返す。
        """
        fields = project.get("fields") or {}
        specs: list[tuple[str, str, dict]] = []
        if anken is not None and "案件" in fields:
            specs.append(("案件", fields["案件"]["id"], {"text": str(anken)}))
        if due is not None and "期日" in fields:
            specs.append(("期日", fields["期日"]["id"], {"date": str(due)}))
        if effort is not None and "工数" in fields:
            try:
                specs.append(("工数", fields["工数"]["id"], {"number": float(effort)}))
            except (TypeError, ValueError):
                pass
        if priority is not None and "優先度" in fields:
            option_id = (fields["優先度"].get("options") or {}).get(priority)
            if option_id:
                specs.append((
                    "優先度", fields["優先度"]["id"],
                    {"singleSelectOptionId": option_id},
                ))

        applied: list[str] = []
        for fname, field_id, value in specs:
            try:
                self.gh.set_field_value(project["id"], item_id, field_id, value)
                applied.append(fname)
            except GitHubError as e:
                print(f"[task] {fname} の設定をスキップ: {e}")
        return applied

    # ── タスク操作 ──────────────────────────────────────────────────────────
    def add(
        self,
        title: str,
        body: str = "",
        project: str | None = None,
        note: str | None = None,
        labels: list[str] | None = None,
        due: str | None = None,
        effort: float | None = None,
        priority: str | None = None,
    ) -> dict:
        """タスク（Issue）を作成し、ボードに登録して各フィールドを設定する。

        - ``project``: 案件名（ボードの「案件」フィールド + Issue 本文）。
        - ``due``: 期日（YYYY-MM-DD）。``effort``: 工数（数値）。
        - ``priority``: 優先度（高 / 中 / 低）。
        - ``note``: 紐づける ZK ノートの ID/パス（Issue 本文 + ノートへ逆リンク）。
        """
        lines = [body] if body else []
        if project:
            lines.append(f"\n**案件:** {project}")
        if due:
            lines.append(f"**期日:** {due}")
        if priority:
            lines.append(f"**優先度:** {priority}")
        if effort is not None:
            lines.append(f"**工数:** {effort}")
        if note:
            lines.append(f"**関連ノート:** {note}")
        full_body = "\n".join(lines).strip()

        issue = self.gh.create_issue(title, full_body, labels)

        board = False
        applied_fields: list[str] = []
        proj = self.gh.ensure_project()
        if proj:
            try:
                item_id = self.gh.add_to_board(proj["id"], issue["node_id"])
                if item_id:
                    option_id = proj["status"]["options"].get("Todo")
                    field_id = proj["status"]["field_id"]
                    if option_id and field_id:
                        self.gh.set_status(proj["id"], item_id, field_id, option_id)
                    applied_fields = self._apply_fields(
                        proj, item_id, anken=project, due=due,
                        effort=effort, priority=priority,
                    )
                    board = True
            except GitHubError as e:
                print(f"[task] ボード登録をスキップ: {e}")

        # ノート → Issue の逆リンク（ノートの frontmatter tasks: に番号を追記）
        linked_note: str | None = None
        if note and self._vault is not None:
            try:
                self._vault.sync()
                rel = self._vault.link_task(note, issue["number"])
                if rel:
                    self._vault.commit_and_push(
                        f"chore: link task #{issue['number']} -> {rel}"
                    )
                    linked_note = rel
            except Exception as e:  # noqa: BLE001 - 逆リンクは best-effort
                print(f"[task] ノートへの逆リンクをスキップ: {e}")

        return {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["url"],
            "status": "Todo" if board else "(ボード未連携)",
            "on_board": board,
            "案件": project,
            "期日": due,
            "工数": effort,
            "優先度": priority,
            "fields_applied": applied_fields,
            "linked_note": linked_note,
        }

    def list(self, status: str | None = None, project: str | None = None) -> list[dict]:
        """タスク一覧を返す（status / 案件 で絞り込み可）。"""
        state = "all"
        if status == "Done":
            state = "closed"
        elif status in ("Todo", "In Progress"):
            state = "open"

        issues = self.gh.list_issues(state=state)

        # ボードのフィールド値を一括取得してマージ
        board_map: dict[int, dict] = {}
        proj = self.gh.ensure_project()
        if proj:
            try:
                board_map = {
                    it["number"]: it for it in self.gh.board_items(proj["id"])
                }
            except GitHubError:
                pass

        out = []
        for it in issues:
            bi = board_map.get(it["number"]) or {}
            st = bi.get("status") or ("Done" if it["state"] == "closed" else "Todo")
            if status and st != status:
                continue
            if project and bi.get("案件") != project:
                continue
            out.append({
                **it,
                "board_status": st,
                "案件": bi.get("案件"),
                "期日": bi.get("期日"),
                "優先度": bi.get("優先度"),
                "工数": bi.get("工数"),
            })
        return out

    def show(self, number: int) -> dict:
        issue = self.gh.get_issue(number)
        bi: dict = {}
        proj = self.gh.ensure_project()
        if proj:
            try:
                for it in self.gh.board_items(proj["id"]):
                    if it["number"] == number:
                        bi = it
                        break
            except GitHubError:
                pass
        issue["board_status"] = bi.get("status") or (
            "Done" if issue["state"] == "closed" else "Todo"
        )
        for key in ("案件", "期日", "優先度", "工数"):
            issue[key] = bi.get(key)
        return issue

    def update(
        self,
        number: int,
        status: str | None = None,
        project: str | None = None,
        due: str | None = None,
        effort: float | None = None,
        priority: str | None = None,
    ) -> dict:
        """タスクの Status / カスタムフィールドを更新する。

        Done にすると Issue もクローズする。
        """
        if status is not None and status not in STATUS_VALUES:
            raise ValueError(f"status は {STATUS_VALUES} のいずれか: {status}")

        board_status_ok: bool | None = None
        if status is not None:
            board_status_ok = self._set_board_status(number, status)
            if status == "Done":
                self.gh.close_issue(number)
            else:
                self.gh.update_issue(number, state="open")

        applied: list[str] = []
        if any(v is not None for v in (project, due, effort, priority)):
            proj = self.gh.ensure_project()
            if proj:
                item_id = self._find_item_id(proj, number)
                if item_id:
                    applied = self._apply_fields(
                        proj, item_id, anken=project, due=due,
                        effort=effort, priority=priority,
                    )
        return {
            "number": number,
            "status": status,
            "board_updated": board_status_ok,
            "fields_updated": applied,
        }

    def done(self, number: int) -> dict:
        return self.update(number, "Done")
