# Release Center

Этот документ генерируется из `VERSION` и `CHANGELOG.md`.
Он показывает release state AIKit как продуктовой платформы, а не только как внутреннего git-репозитория.

- Current version: `0.1.0`
- Latest released version: `0.1.0`
- Latest release date: `2026-04-20`

## Should I Update?

- Compatibility verdict: `compatible with current install/update flows`
- Breaking changes: `none declared in Unreleased`
- Update verdict: Local support analytics and release candidate evidence triage is staged for review. No release is published.
- Candidate review status: `candidate-review-only`
- Claude workspace update: `bash .aikit-config/scripts/update.sh`
- Runtime workspace update command: `/aikit-runtime-workspace <adapter> --preset <preset> --workspace <path> --operation update`
- Runtime workspace command wraps install/update/bootstrap implementation details.
- Release details: see `CHANGELOG.md` and the `Unreleased` section below.

## Current State

- Source of truth version file: [`VERSION`](../../VERSION)
- Changelog source: [`CHANGELOG.md`](../../CHANGELOG.md)
- Release validation: `/aikit-doctor --check validate-release`
- Release prep flow: `/aikit-command-center release --version <semver> --date YYYY-MM-DD`

## Unreleased

### Added
- Support analytics and release candidate evidence triage for local review. No release is published by this entry.

## Latest Release Snapshot

### `0.1.0` — 2026-04-20

### Added
- Формализован spec layer для manifests и schemas.
- Введены adapter manifests, package/install flows и conformance matrix для Claude, Codex, GLM и OpenCode.
- Введён canonical memory model с `.aikit/memory/` и Claude mirror.
- Введён workflow policy engine с fixtures для `intent` и `next_action`.
- Добавлен packaged maintainer flow и operational planning layer через roadmap и execution log.

### Changed
- `attach.sh` и `update.sh` теперь опираются на root `VERSION` как основной source of truth для версии AIKit.
- Multi-runtime архитектура стала first-class частью репозитория, а не только направлением в prose.

## Release Workflow

1. Обновить `CHANGELOG.md` в секции `Unreleased`.
2. Подготовить следующий релиз через `/aikit-command-center release --version <semver> --date YYYY-MM-DD`.
3. Прогнать `/aikit-doctor --check validate-release` и `/aikit-doctor --check validate-config`.
4. Если менялись installer/build/docs scripts, прогнать `py_compile`, `bash -n` и product generators.
5. Не готовить релиз, пока `Unreleased` содержит только placeholder `- Пока пусто.`.

## Product Signals

- Release version встраивается в adapter packages как `repo_version`.
- Install/update flows используют root `VERSION` как source of truth.
- Generated docs позволяют смотреть release/install состояние без чтения кода скриптов.
