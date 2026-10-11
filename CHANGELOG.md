# Changelog

Все заметные изменения в AIKit фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/)
и использует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added
- Support analytics and release candidate evidence triage for local review. No release is published by this entry.

## [0.1.0] - 2026-04-20

### Added
- Формализован spec layer для manifests и schemas.
- Введены adapter manifests, package/install flows и conformance matrix для Claude, Codex, GLM и OpenCode.
- Введён canonical memory model с `.aikit/memory/` и Claude mirror.
- Введён workflow policy engine с fixtures для `intent` и `next_action`.
- Добавлен `aikit-maintainer` и operational planning layer через roadmap и execution log.

### Changed
- `attach.sh` и `update.sh` теперь опираются на root `VERSION` как основной source of truth для версии AIKit.
- Multi-runtime архитектура стала first-class частью репозитория, а не только направлением в prose.
