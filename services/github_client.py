from __future__ import annotations
import base64
from datetime import datetime, timezone
from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile
import config


class GitHubClient:
    def __init__(self) -> None:
        self._gh = Github(config.GITHUB_TOKEN)
        self._repo: Repository = self._gh.get_repo(config.GITHUB_REPO)
        self._cache: dict[str, tuple[str, datetime]] = {}
        self._cache_ttl_seconds: int = 300

    # ── Read ──────────────────────────────────────────────────────────────────

    def read_file(self, path: str, use_cache: bool = True) -> str:
        if use_cache and path in self._cache:
            content, fetched_at = self._cache[path]
            age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return content

        try:
            cf: ContentFile = self._repo.get_contents(path)
            text = base64.b64decode(cf.content).decode("utf-8")
        except GithubException as e:
            if e.status == 404:
                raise FileNotFoundError(f"GitHub path not found: {path}") from e
            raise

        self._cache[path] = (text, datetime.now(timezone.utc))
        return text

    def read_system_prompt(self) -> str:
        return self.read_file(config.SYSTEM_PROMPT_PATH)

    def read_prompt(self, command: str) -> str:
        return self.read_file(f"{config.PROMPTS_PATH}/{command}.md")

    def read_template(self, name: str) -> str:
        return self.read_file(f"{config.TEMPLATES_PATH}/{name}.md")

    def read_user_profile(self) -> str:
        return self.read_file("_config/user-profile.md")

    # ── Write ─────────────────────────────────────────────────────────────────

    def create_or_update_file(
        self,
        path: str,
        content: str,
        commit_message: str,
    ) -> str:
        try:
            existing: ContentFile = self._repo.get_contents(path)
            result = self._repo.update_file(
                path=path,
                message=commit_message,
                content=content,
                sha=existing.sha,
            )
        except GithubException as e:
            if e.status == 404:
                result = self._repo.create_file(
                    path=path,
                    message=commit_message,
                    content=content,
                )
            else:
                raise

        self._cache.pop(path, None)
        return result["commit"].sha

    def commit_note(
        self,
        path: str,
        content: str,
        note_id: str,
        command: str,
    ) -> str:
        msg = f"add({command}): {note_id}"
        return self.create_or_update_file(path, content, msg)

    def commit_inbox(self, path: str, content: str, filename: str) -> str:
        msg = f"inbox: {filename}"
        return self.create_or_update_file(path, content, msg)
