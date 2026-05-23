"""GitHub タスク連携クライアント。

タスクの実体は **GitHub Issue**（REST API）、ビューは **Projects v2 ボード**
（GraphQL API）。Issue が source of truth で、Projects v2 への登録・Status 設定は
ベストエフォート（失敗しても Issue は作成される）。

`GITHUB_TOKEN`（repo + project スコープ）と `GITHUB_REPO`（owner/repo）が必要。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import config

_REST = "https://api.github.com"
_GQL = "https://api.github.com/graphql"

# Projects v2 の Status フィールドで使う値
STATUS_VALUES = ("Todo", "In Progress", "Done")

# 優先度フィールドの選択肢
PRIORITY_VALUES = ("高", "中", "低")

# Projects v2 に用意するカスタムフィールド（名前 → データ型）
# 工数は単位ごと（時間/日）に独立した数値フィールドを持つ。
_CUSTOM_FIELD_TYPES = {
    "案件": "TEXT",
    "期日": "DATE",
    "工数(時間)": "NUMBER",
    "工数(日)": "NUMBER",
    "優先度": "SINGLE_SELECT",
}


class GitHubError(RuntimeError):
    """GitHub API 呼び出しの失敗。"""


class GitHubTasks:
    def __init__(self) -> None:
        if not config.GITHUB_TOKEN:
            raise GitHubError("GITHUB_TOKEN が未設定です（タスク管理に必要）。")
        if "/" not in config.GITHUB_REPO:
            raise GitHubError("GITHUB_REPO は 'owner/repo' 形式で設定してください。")
        self.owner, self.repo = config.GITHUB_REPO.split("/", 1)
        self._token = config.GITHUB_TOKEN
        self._project_cache: dict | None = None

    # ── 低レベル HTTP ───────────────────────────────────────────────────────
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "second-brain-engine",
        }

    def _rest(self, method: str, path: str, body: dict | None = None) -> dict | list:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            _REST + path, data=data, method=method, headers=self._headers()
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise GitHubError(f"GitHub REST {method} {path}: {e.code} {e.read().decode('utf-8', 'ignore')}") from e

    def _gql(self, query: str, variables: dict) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        req = urllib.request.Request(_GQL, data=body, method="POST", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise GitHubError(f"GitHub GraphQL: {e.code} {e.read().decode('utf-8', 'ignore')}") from e
        if payload.get("errors"):
            raise GitHubError(f"GitHub GraphQL: {payload['errors']}")
        return payload["data"]

    # ── Issues（タスクの実体） ──────────────────────────────────────────────
    def create_issue(self, title: str, body: str = "", labels: list[str] | None = None) -> dict:
        issue = self._rest(
            "POST", f"/repos/{self.owner}/{self.repo}/issues",
            {"title": title, "body": body, "labels": labels or []},
        )
        return {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["html_url"],
            "node_id": issue["node_id"],
            "state": issue["state"],
        }

    def list_issues(self, state: str = "open") -> list[dict]:
        items = self._rest(
            "GET",
            f"/repos/{self.owner}/{self.repo}/issues"
            f"?state={state}&per_page=100&filter=all",
        )
        out = []
        for it in items:
            if "pull_request" in it:  # PR は除外
                continue
            out.append({
                "number": it["number"],
                "title": it["title"],
                "url": it["html_url"],
                "state": it["state"],
                "labels": [lb["name"] for lb in it.get("labels", [])],
            })
        return out

    def get_issue(self, number: int) -> dict:
        it = self._rest("GET", f"/repos/{self.owner}/{self.repo}/issues/{number}")
        return {
            "number": it["number"], "title": it["title"], "url": it["html_url"],
            "state": it["state"], "body": it.get("body", ""),
            "node_id": it["node_id"],
            "labels": [lb["name"] for lb in it.get("labels", [])],
        }

    def update_issue(self, number: int, **fields: object) -> dict:
        it = self._rest(
            "PATCH", f"/repos/{self.owner}/{self.repo}/issues/{number}", dict(fields)
        )
        return {"number": it["number"], "state": it["state"], "url": it["html_url"]}

    def close_issue(self, number: int) -> dict:
        return self.update_issue(number, state="closed")

    # ── Projects v2（ビュー） ───────────────────────────────────────────────
    def _owner_id(self) -> str:
        data = self._gql(
            "query($l:String!){ repositoryOwner(login:$l){ id } }", {"l": self.owner}
        )
        owner = data.get("repositoryOwner")
        if not owner:
            raise GitHubError(f"owner が見つかりません: {self.owner}")
        return owner["id"]

    def ensure_project(self) -> dict | None:
        """Projects v2 ボードを取得（無ければ作成）し、Status フィールド情報を返す。

        探索順: GITHUB_PROJECT_NUMBER → 同名 Project（最古を採用） → 新規作成。
        2 段階目のタイトル検索により、番号未設定でも既存ボードを再利用でき、
        デーモン起動のたびに空ボードを量産する不具合を防ぐ。失敗時は None を
        返す（Issue 運用は継続できる）。
        """
        if self._project_cache is not None:
            return self._project_cache
        try:
            number = config.GITHUB_PROJECT_NUMBER
            project = None
            if number:
                data = self._gql(
                    "query($l:String!,$n:Int!){ user(login:$l){ projectV2(number:$n){ id title } } "
                    "organization(login:$l){ projectV2(number:$n){ id title } } }",
                    {"l": self.owner, "n": number},
                )
                holder = data.get("user") or data.get("organization") or {}
                project = holder.get("projectV2")
            if project is None:
                # 番号未設定/誤指定でも、同名の既存 Project があれば再利用する。
                project = self._find_project_by_title(config.GITHUB_PROJECT_TITLE)
            if project is None:
                # それでも見つからなければ新規作成。
                created = self._gql(
                    "mutation($o:ID!,$t:String!){ createProjectV2(input:{ownerId:$o,title:$t})"
                    "{ projectV2{ id title number } } }",
                    {"o": self._owner_id(), "t": config.GITHUB_PROJECT_TITLE},
                )
                project = created["createProjectV2"]["projectV2"]

            status = self._status_field(project["id"])
            fields = self._ensure_custom_fields(project["id"])
            self._project_cache = {
                "id": project["id"], "status": status, "fields": fields,
            }
            return self._project_cache
        except GitHubError as e:
            print(f"[github_tasks] Projects v2 連携をスキップ: {e}")
            return None

    def _find_project_by_title(self, title: str) -> dict | None:
        """ユーザー/Org の Projects から指定タイトルの非クローズ Project を探す。

        複数あれば番号が最小（＝最古）のものを返す。
        """
        data = self._gql(
            "query($l:String!){ "
            "user(login:$l){ projectsV2(first:50){ nodes{ id title number closed } } } "
            "organization(login:$l){ projectsV2(first:50){ nodes{ id title number closed } } } "
            "}",
            {"l": self.owner},
        )
        candidates: list[dict] = []
        for holder_key in ("user", "organization"):
            holder = data.get(holder_key) or {}
            nodes = (holder.get("projectsV2") or {}).get("nodes") or []
            for n in nodes:
                if n and n.get("title") == title and not n.get("closed"):
                    candidates.append(n)
        if not candidates:
            return None
        candidates.sort(key=lambda n: n["number"])
        n = candidates[0]
        return {"id": n["id"], "title": n["title"], "number": n["number"]}

    def _status_field(self, project_id: str) -> dict:
        data = self._gql(
            "query($p:ID!){ node(id:$p){ ... on ProjectV2 { field(name:\"Status\"){ "
            "... on ProjectV2SingleSelectField { id options{ id name } } } } } }",
            {"p": project_id},
        )
        field = (data.get("node") or {}).get("field") or {}
        options = {o["name"]: o["id"] for o in field.get("options", [])}
        return {"field_id": field.get("id"), "options": options}

    # ── Projects v2 カスタムフィールド（案件・期日・優先度・工数） ──────────
    def _ensure_custom_fields(self, project_id: str) -> dict:
        """カスタムフィールドを確認し、無ければ作成する（best-effort）。

        戻り値: {フィールド名: {"id": str, "options": {選択肢名: ID}}}。
        """
        existing = self._list_fields(project_id)
        # 旧フィールド「工数」を「工数(時間)」へリネーム（既定単位を時間として継承）。
        if "工数" in existing and "工数(時間)" not in existing:
            try:
                self._rename_field(existing["工数"]["id"], "工数(時間)")
                existing = self._list_fields(project_id)
            except GitHubError as e:
                print(f"[github_tasks] 工数→工数(時間) のリネームに失敗: {e}")
        out: dict = {}
        for name, dtype in _CUSTOM_FIELD_TYPES.items():
            if name in existing:
                out[name] = existing[name]
                continue
            try:
                created = self._create_field(project_id, name, dtype)
                if created:
                    out[name] = created
            except GitHubError as e:
                print(f"[github_tasks] フィールド作成をスキップ ({name}): {e}")
        return out

    def _rename_field(self, field_id: str, new_name: str) -> None:
        self._gql(
            "mutation($f:ID!,$n:String!){ updateProjectV2Field(input:{fieldId:$f,"
            "name:$n}){ projectV2Field{ ... on ProjectV2FieldCommon { id name } } } }",
            {"f": field_id, "n": new_name},
        )

    def _list_fields(self, project_id: str) -> dict:
        data = self._gql(
            "query($p:ID!){ node(id:$p){ ... on ProjectV2 { fields(first:50){ nodes{ "
            "... on ProjectV2FieldCommon { id name } "
            "... on ProjectV2SingleSelectField { id name options{ id name } } "
            "} } } } }",
            {"p": project_id},
        )
        nodes = (((data.get("node") or {}).get("fields")) or {}).get("nodes") or []
        out: dict = {}
        for n in nodes:
            if not n or "name" not in n:
                continue
            options = {o["name"]: o["id"] for o in (n.get("options") or [])}
            out[n["name"]] = {"id": n["id"], "options": options}
        return out

    def _create_field(self, project_id: str, name: str, dtype: str) -> dict | None:
        if dtype == "SINGLE_SELECT":
            # 優先度: 高/中/低 を固定の選択肢として作成する。
            options_gql = (
                '{name:"高",color:RED,description:""},'
                '{name:"中",color:YELLOW,description:""},'
                '{name:"低",color:GRAY,description:""}'
            )
            data = self._gql(
                "mutation($p:ID!,$n:String!){ createProjectV2Field(input:{projectId:$p,"
                "dataType:SINGLE_SELECT,name:$n,singleSelectOptions:[" + options_gql
                + "]}){ projectV2Field{ "
                "... on ProjectV2SingleSelectField { id name options{ id name } } } } }",
                {"p": project_id, "n": name},
            )
        else:
            data = self._gql(
                "mutation($p:ID!,$n:String!,$t:ProjectV2CustomFieldType!){ "
                "createProjectV2Field(input:{projectId:$p,dataType:$t,name:$n}){ "
                "projectV2Field{ ... on ProjectV2FieldCommon { id name } } } }",
                {"p": project_id, "n": name, "t": dtype},
            )
        field = (data.get("createProjectV2Field") or {}).get("projectV2Field") or {}
        if not field.get("id"):
            return None
        options = {o["name"]: o["id"] for o in (field.get("options") or [])}
        return {"id": field["id"], "options": options}

    def set_field_value(
        self, project_id: str, item_id: str, field_id: str, value: dict
    ) -> None:
        """ボード項目のフィールド値を設定する。

        value 例: {"text": "案件名"} / {"date": "2026-05-30"} / {"number": 3}
                  / {"singleSelectOptionId": "..."}
        """
        self._gql(
            "mutation($p:ID!,$i:ID!,$f:ID!,$v:ProjectV2FieldValue!){ "
            "updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,"
            "value:$v}){ projectV2Item{ id } } }",
            {"p": project_id, "i": item_id, "f": field_id, "v": value},
        )

    def add_to_board(self, project_id: str, issue_node_id: str) -> str:
        data = self._gql(
            "mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p,contentId:$c})"
            "{ item{ id } } }",
            {"p": project_id, "c": issue_node_id},
        )
        return data["addProjectV2ItemById"]["item"]["id"]

    def board_items(self, project_id: str) -> list[dict]:
        """ボード上の項目（Issue 番号・item ID・各フィールド値）を一覧で返す。"""
        data = self._gql(
            "query($p:ID!){ node(id:$p){ ... on ProjectV2 { items(first:100){ nodes{ id "
            "content{ ... on Issue { number } } "
            'status: fieldValueByName(name:"Status"){ '
            "... on ProjectV2ItemFieldSingleSelectValue { name } } "
            'anken: fieldValueByName(name:"案件"){ '
            "... on ProjectV2ItemFieldTextValue { text } } "
            'kijitsu: fieldValueByName(name:"期日"){ '
            "... on ProjectV2ItemFieldDateValue { date } } "
            'yusen: fieldValueByName(name:"優先度"){ '
            "... on ProjectV2ItemFieldSingleSelectValue { name } } "
            'kosuH: fieldValueByName(name:"工数(時間)"){ '
            "... on ProjectV2ItemFieldNumberValue { number } } "
            'kosuD: fieldValueByName(name:"工数(日)"){ '
            "... on ProjectV2ItemFieldNumberValue { number } } } } } } }",
            {"p": project_id},
        )
        nodes = (((data.get("node") or {}).get("items")) or {}).get("nodes") or []
        out = []
        for n in nodes:
            content = n.get("content") or {}
            if "number" not in content:
                continue
            out.append({
                "item_id": n["id"],
                "number": content["number"],
                "status": (n.get("status") or {}).get("name"),
                "案件": (n.get("anken") or {}).get("text"),
                "期日": (n.get("kijitsu") or {}).get("date"),
                "優先度": (n.get("yusen") or {}).get("name"),
                "工数(時間)": (n.get("kosuH") or {}).get("number"),
                "工数(日)": (n.get("kosuD") or {}).get("number"),
            })
        return out

    def set_status(self, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
        self._gql(
            "mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue("
            "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}})"
            "{ projectV2Item{ id } } }",
            {"p": project_id, "i": item_id, "f": field_id, "o": option_id},
        )
