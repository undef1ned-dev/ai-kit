#!/usr/bin/env python3
"""
Tests of scripts/bump-version.py: the level from commit messages, the next version, the changelog
section and a run on a temporary git repository. The workflow paths must match PLUGIN_PATHS.

Usage:
    python3 scripts/ci/test-bump-version.py
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "bump-version.py"
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "version.yml"

LEVELS = [
    ("feat → minor", ["feat(deck): добавлена кнопка"], "minor"),
    ("fix → patch", ["fix: исправлено падение"], "patch"),
    ("docs, chore, refactor → patch", ["docs: правка", "chore(deps): обновлено", "refactor: вынесено"], "patch"),
    ("perf, build, ci, test, style → patch", ["perf: быстрее", "build: сборка", "ci: шаг", "test: сценарий", "style: отступы"], "patch"),
    ("! в заголовке → major", ["feat(profiles)!: удалён профиль"], "major"),
    ("! без scope → major", ["refactor!: новый формат контракта"], "major"),
    ("BREAKING CHANGE в футере → major", ["fix: формат\n\nBREAKING CHANGE: ключ commands переименован"], "major"),
    ("BREAKING-CHANGE в футере → major", ["chore: x\n\nBREAKING-CHANGE: y"], "major"),
    ("старший уровень побеждает", ["fix: a", "feat: b", "docs: c"], "minor"),
    ("не по Conventional Commits → patch", ["обновил README"], "patch"),
    ("squash-слияние с номером PR", ["feat(codex): модель уровня opus (#29)"], "minor"),
    ("merge-коммит не считается", ["Merge pull request #28 from x/y"], None),
    ("прошлый релиз не считается", ["chore(release): v0.2.0"], None),
    ("нет коммитов → без релиза", [], None),
    ("слово breaking в тексте — не major", ["fix: breaking change in parser fixed"], "patch"),
]

VERSIONS = [
    ("0.1.0", "patch", "0.1.1"),
    ("0.1.9", "minor", "0.2.0"),
    ("0.2.3", "major", "1.0.0"),
    ("1.9.9", "patch", "1.9.10"),
]

PLUGIN_FILES = [
    ("base/ — в плагине", ["base/skills/x/SKILL.md"], True),
    ("profiles/ — в плагине", ["profiles/vue-nuxt/agents/a.md"], True),
    ("deck/ — в плагине", ["deck/catalog.js"], True),
    ("scripts/ — в плагине", ["scripts/plugin-init.py"], True),
    ("манифест — в плагине", [".claude-plugin/marketplace.json"], True),
    ("docs/ — нет", ["docs/guide/x.md", "docs/site/x.html"], False),
    ("evals/ и CI — нет", ["evals/core/x/prompt.md", ".github/workflows/ci.yml", "scripts/ci/test-hooks.py"], False),
    ("тесты деки — нет", ["deck/tests/catalog.test.js"], False),
    ("README и CHANGELOG — нет", ["README.md", "CHANGELOG.md"], False),
]

CHANGELOG = """# Changelog

## [Unreleased]

### Added
- Ручная заметка.

## [0.1.0] - 2026-04-20

### Added
- Первый релиз.
"""


def load_script():
    sys.path.insert(0, str(KIT_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("aikit_bump_version", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workflow_paths() -> list[str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("    paths:\n", 1)[1]
    return re.findall(r'^      - "([^"]+)/\*\*"$', block.split("  workflow_dispatch:", 1)[0], flags=re.MULTILINE)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True, encoding="utf-8")
    return result.stdout


def commit(repo: Path, path: str, message: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8", newline="\n") as file:
        file.write(f"{message}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def make_repo(root: Path) -> Path:
    repo = root / "kit"
    (repo / "scripts").mkdir(parents=True)
    for name in ("bump-version.py", "release_utils.py"):
        shutil.copyfile(KIT_ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / "VERSION").write_bytes(b"0.1.0\n")
    (repo / "CHANGELOG.md").write_bytes(CHANGELOG.encode("utf-8"))
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(release): v0.1.0")
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "bump-version.py"), *args],
        cwd=repo, capture_output=True, encoding="utf-8",
    )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    failures: list[str] = []

    def expect(name: str, condition: bool, details: str = "") -> None:
        print(f"  {'✓' if condition else '✗'} {name}")
        if not condition:
            failures.append(f"{name}: {details}")

    bump = load_script()

    print("▶ Уровень по сообщениям коммитов")
    for name, messages, expected in LEVELS:
        level = bump.bump_level(messages)
        expect(name, level == expected, f"{level}, ожидался {expected}")

    print("▶ Следующая версия")
    for current, level, expected in VERSIONS:
        result = bump.next_version(current, level)
        expect(f"{current} + {level} → {expected}", result == expected, result)

    print("▶ Что попадает в плагины")
    for name, files, expected in PLUGIN_FILES:
        expect(name, bump.touches_plugins(files) == expected)
    expect(
        "paths в version.yml совпадают с PLUGIN_PATHS",
        [f"{path}/" for path in workflow_paths()] == list(bump.PLUGIN_PATHS),
        f"{workflow_paths()} ≠ {bump.PLUGIN_PATHS}",
    )

    print("▶ Секция CHANGELOG")
    section = bump.changelog_section("0.2.0", "2026-10-21", [
        "feat(deck): добавлена кнопка",
        "fix: исправлено падение (#30)",
        "refactor!: новый формат контракта",
        "docs: обновлена страница",
        "Merge pull request #30 from x/y",
    ])
    expect("заголовок версии", section.startswith("## [0.2.0] - 2026-10-21\n"), section)
    expect("feat → Added со scope", "### Added\n- deck: добавлена кнопка" in section, section)
    expect("breaking — первым в Changed", "### Changed\n- **Несовместимо.** новый формат контракта\n- обновлена страница" in section, section)
    expect("fix → Fixed", "### Fixed\n- исправлено падение (#30)" in section, section)
    expect("merge-коммит не в списке", "Merge" not in section, section)
    updated = bump.insert_section(CHANGELOG, section)
    expect(
        "секция — после [Unreleased], перед прошлым релизом",
        updated.index("## [Unreleased]") < updated.index("## [0.2.0]") < updated.index("## [0.1.0]")
        and "- Ручная заметка." in updated,
        updated,
    )

    print("▶ Прогон на git-репозитории")
    with tempfile.TemporaryDirectory() as temp:
        repo = make_repo(Path(temp))
        commit(repo, "docs/guide/a.md", "feat(docs): новая страница")
        commit(repo, ".github/workflows/ci.yml", "ci: шаг")
        result = run(repo, "--write")
        expect(
            "только docs и CI — версия не меняется",
            result.returncode == 0 and (repo / "VERSION").read_text(encoding="utf-8") == "0.1.0\n",
            result.stdout + result.stderr,
        )
        commit(repo, "base/skills/x/SKILL.md", "fix(skills): правка скилла")
        commit(repo, "deck/catalog.js", "feat(deck): новая группа")
        git(repo, "checkout", "-q", "-b", "feat/x")
        commit(repo, "profiles/p/agents/a.md", "refactor(profiles): агент")
        git(repo, "checkout", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "-m", "Merge pull request #1 from x/feat-x", "feat/x")
        result = run(repo, "--write")
        changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        expect(
            "feat в deck/ → 0.2.0",
            result.returncode == 0 and (repo / "VERSION").read_text(encoding="utf-8") == "0.2.0\n",
            result.stdout + result.stderr,
        )
        expect(
            "в CHANGELOG коммиты плагинов, без docs и merge",
            "- deck: новая группа" in changelog and "- skills: правка скилла" in changelog
            and "- profiles: агент" in changelog and "новая страница" not in changelog and "Merge" not in changelog,
            changelog,
        )
        expect("файлы с LF", b"\r" not in (repo / "CHANGELOG.md").read_bytes() + (repo / "VERSION").read_bytes())
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "chore(release): v0.2.0")
        result = run(repo, "--write")
        expect(
            "сразу после релиза — без нового релиза",
            result.returncode == 0 and (repo / "VERSION").read_text(encoding="utf-8") == "0.2.0\n",
            result.stdout + result.stderr,
        )
        commit(repo, "packs/d/agents/a.md", "feat(packs)!: пак переписан")
        result = run(repo)
        expect(
            "без --write только печать, breaking → 1.0.0",
            "0.2.0 → 1.0.0" in result.stdout and (repo / "VERSION").read_text(encoding="utf-8") == "0.2.0\n",
            result.stdout + result.stderr,
        )

    if failures:
        print(f"✗ bump-version: не пройдено {len(failures)}")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("✓ bump-version: все сценарии пройдены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
