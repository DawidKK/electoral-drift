#!/usr/bin/env python3
"""Trigger an architecture-documentation audit after relevant repo changes."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


WATCHED_DIRECTORIES = ("apps", "packages", "docs/adr")

WATCHED_FILES = (
    ".env.example",
    "AGENTS.md",
    "CONTEXT.md",
    "alembic.ini",
    "docker-compose.yml",
    "docs/api_contract.md",
    "docs/database_schema.md",
    "docs/flow.md",
    "docs/ingestion.md",
    "docs/teryt_mapping.md",
    "pyproject.toml",
)

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tld",
    ".venv",
    "__pycache__",
    "data",
    "dist",
    "node_modules",
}

MAX_CHANGED_PATHS_IN_PROMPT = 50


def emit(payload: Mapping[str, object]) -> None:
    """Write one valid hook response to stdout."""
    print(json.dumps(payload, ensure_ascii=False))


def read_event() -> Mapping[str, object]:
    """Read the event envelope supplied by Codex on stdin."""
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    return payload


def find_repository(event: Mapping[str, object]) -> Path:
    """Resolve the repository root from the event working directory."""
    event_cwd = event.get("cwd")
    cwd = Path(event_cwd if isinstance(event_cwd, str) else os.getcwd())
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def state_path(repository: Path, event: Mapping[str, object]) -> Path:
    """Return a session-specific state path outside the working tree."""
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "unknown-session"

    state_root_override = os.environ.get("CODEX_TLD_HOOK_STATE_DIR")
    state_root = (
        Path(state_root_override)
        if state_root_override
        else Path(tempfile.gettempdir()) / "electoral-drift-codex-hooks"
    )
    state_root.mkdir(parents=True, exist_ok=True)
    state_key = hashlib.sha256(
        (str(repository) + "\0" + session_id).encode("utf-8")
    ).hexdigest()
    return state_root / (state_key + ".json")


def is_ignored(path: Path, repository: Path) -> bool:
    """Exclude generated, cached, dependency, data, and tld content."""
    relative_parts = path.relative_to(repository).parts
    return any(part in IGNORED_DIRECTORY_NAMES for part in relative_parts)


def watched_paths(repository: Path) -> Iterable[Path]:
    """Yield relevant source and routed-document files without symlinks."""
    yielded = set()

    for relative_path in WATCHED_FILES:
        candidate = repository / relative_path
        if candidate.is_file() and not candidate.is_symlink():
            yielded.add(candidate)
            yield candidate

    for relative_directory in WATCHED_DIRECTORIES:
        directory = repository / relative_directory
        if not directory.is_dir():
            continue
        for candidate in directory.rglob("*"):
            if (
                candidate in yielded
                or not candidate.is_file()
                or candidate.is_symlink()
                or is_ignored(candidate, repository)
            ):
                continue
            yielded.add(candidate)
            yield candidate


def digest(path: Path) -> str:
    """Hash content so timestamps alone do not trigger an audit."""
    file_hash = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            file_hash.update(chunk)
    return file_hash.hexdigest()


def snapshot(repository: Path) -> Dict[str, str]:
    """Build a deterministic snapshot of architecture-relevant files."""
    paths = sorted(watched_paths(repository), key=lambda path: str(path))
    return {
        str(path.relative_to(repository)): digest(path)
        for path in paths
    }


def load_snapshot(path: Path) -> Dict[str, str]:
    """Load a previous baseline, treating an invalid file as absent."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def save_snapshot(path: Path, current: Mapping[str, str]) -> None:
    """Persist the new baseline atomically."""
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(current, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(str(temporary_path), str(path))


def changed_paths(
    previous: Mapping[str, str], current: Mapping[str, str]
) -> List[str]:
    """Describe added, deleted, and modified paths."""
    changes = []
    for relative_path in sorted(set(previous) | set(current)):
        if relative_path not in previous:
            changes.append("A " + relative_path)
        elif relative_path not in current:
            changes.append("D " + relative_path)
        elif previous[relative_path] != current[relative_path]:
            changes.append("M " + relative_path)
    return changes


def continuation_prompt(changes: List[str]) -> str:
    """Create the prompt Codex receives when Stop blocks completion."""
    visible_changes = changes[:MAX_CHANGED_PATHS_IN_PROMPT]
    change_lines = "\n".join("- " + change for change in visible_changes)
    hidden_count = len(changes) - len(visible_changes)
    if hidden_count:
        change_lines += "\n- ... oraz {} dalszych plików".format(hidden_count)

    return """$create-diagram

To jest automatyczna kontrola architektury po pracy nad feature. Nie zakładaj,
że każda zmiana pliku wymaga zmiany diagramu lub dokumentacji.

Pliki zmienione od początku sesji:
{change_lines}

Wykonaj audyt semantyczny:

1. Przeczytaj instrukcje repozytorium oraz cały skill `create-diagram`. Sprawdź
   wskazane zmiany i powiązany aktualny kod. Kod w bieżącym working tree jest
   źródłem prawdy; zaakceptowane ADR-y i dokumentacja domenowa definiują
   obowiązujące ograniczenia.
2. Ustal, czy zmieniły się granice komponentów, zależności, główny przepływ
   aplikacji, model domenowy albo schemat danych. Dla zmian wyłącznie testowych,
   formatowania lub refaktoryzacji bez wpływu architektonicznego nie wymuszaj
   sztucznej edycji dokumentacji.
3. Jeżeli architektura się zmieniła, zaktualizuj workspace `.tld` zgodnie ze
   skillem. Elementy i połączenia zmieniaj komendami `tld`, a dokładne komendy
   dopisz do `.tld/diagram.sh`; nie edytuj ręcznie plików generowanych workspace.
4. Zweryfikuj i w razie potrzeby zaktualizuj wszystkie dokumenty routowane:
   - `docs/flow.md` — gdy zmienił się flow lub odpowiedzialność komponentów;
     zachowaj polski tekst i etykiety Mermaid oraz dodaj tylko jeden nowy wpis
     flow-log, jeżeli feature nie jest już odnotowany,
   - `CONTEXT.md` — tylko gdy zmienił się język domenowy, pojęcia lub inwarianty,
   - `docs/database_schema.md` — tylko gdy zmienił się zaimplementowany lub
     wymagany schemat, relacje, ograniczenia albo warstwa analytics/ML.
   Brak potrzeby edycji danego dokumentu jest poprawnym wynikiem audytu.
5. Uruchom `tld validate --strictness 1` oraz
   `tld plan --target local --strictness 1`. Nie uruchamiaj `tld apply`, nie
   synchronizuj z chmurą. Na końcu krótko wypisz, co zaktualizowano, co nie
   wymagało zmian i wyniki obu kontroli.
""".format(change_lines=change_lines)


def handle_start(event: Mapping[str, object]) -> None:
    repository = find_repository(event)
    save_snapshot(state_path(repository, event), snapshot(repository))
    emit({"continue": True})


def handle_stop(event: Mapping[str, object]) -> None:
    repository = find_repository(event)
    path = state_path(repository, event)
    current = snapshot(repository)

    # The hook continuation gets one pass, then establishes the next baseline.
    if event.get("stop_hook_active") is True:
        save_snapshot(path, current)
        emit({"continue": True})
        return

    previous = load_snapshot(path)
    if not previous:
        save_snapshot(path, current)
        emit({"continue": True})
        return

    changes = changed_paths(previous, current)
    if not changes:
        emit({"continue": True})
        return

    emit({"decision": "block", "reason": continuation_prompt(changes)})


def handle_cleanup(event: Mapping[str, object]) -> None:
    repository = find_repository(event)
    path = state_path(repository, event)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"start", "stop", "cleanup"}:
        print("usage: tld_architecture_guard.py start|stop|cleanup", file=sys.stderr)
        return 2

    mode = sys.argv[1]
    try:
        event = read_event()
        if mode == "start":
            handle_start(event)
        elif mode == "stop":
            handle_stop(event)
        else:
            handle_cleanup(event)
    except Exception as error:  # A broken helper must not lock a Codex session.
        if mode != "cleanup":
            emit(
                {
                    "continue": True,
                    "systemMessage": "Architecture hook skipped: {}".format(error),
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
