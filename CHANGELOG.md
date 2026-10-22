# Changelog

Все заметные изменения в AIKit фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/)
и использует [Semantic Versioning](https://semver.org/lang/ru/).

Начиная с 0.2.0 секции версий пишет `scripts/bump-version.py` после слияния в `main` — из сообщений коммитов.
`[Unreleased]` — для ручных заметок, автоматика его не трогает.

## [Unreleased]

### Added
- Support analytics and release candidate evidence triage for local review. No release is published by this entry.

## [0.7.0] - 2026-10-22

### Added
- deck: блок «Действия проекта» и кнопки обновления кита и профиля

## [0.6.0] - 2026-10-22

### Added
- skills: флаги --no-test и --no-review в implement-feature и fix-bug

## [0.5.0] - 2026-10-21

### Added
- plugins: команда $aikit:update-agents обновляет агентов Codex

## [0.4.0] - 2026-10-21

### Added
- models: уровень Codex у архитектора forge-1-12-java снижен до medium (#36)

## [0.3.4] - 2026-10-21

### Changed
- agents: снижен расход токенов агентов, задан effort

## [0.3.3] - 2026-10-21

### Fixed
- plugins: runtime в plugin-init.json хранится списком и не затирается повторным запуском (#34)

## [0.3.2] - 2026-10-21

### Changed
- product: из шаблона PRODUCT.md убраны аудитория, метрики и контакты команды (#33)

## [0.3.1] - 2026-10-21

### Changed
- skills: правило .cmd для npx и npm распространено на команды профиля

## [0.3.0] - 2026-10-21

### Added
- hooks: отметки запусков хуков, --status и проверка готовности в setup

### Fixed
- hooks: лаунчер Codex на Windows передаёт событие Python 3.9+, если python в PATH старый

## [0.2.0] - 2026-10-21

### Added
- plugins: у плагинов Claude Code и Codex и записей маркетплейса есть `version` из `VERSION` — установленные плагины обновляются при её росте.
- release: версия растёт автоматически после слияния в `main` — `scripts/bump-version.py` выбирает major, minor или patch по Conventional Commits и пишет эту секцию.
- hooks: при старте сессии плагин один раз на версию сообщает, что в `main` вышла новая версия AIKit; проверка раз в сутки в фоне, отключается `AIKIT_NO_UPDATE_CHECK=1` или `update_check: false`.
- С 0.1.0: маркетплейс плагинов и `/aikit:setup`, хуки, общий `/implement-feature` по контракту профиля, командная память, панель AIKit Deck, эвалы, уровни моделей агентов — подробно в `docs/roadmap.md`.

### Changed
- **Несовместимо.** С 0.1.0 переработаны контракт профиля и состав кита: удалены python-профили, адаптер GLM, `/workflow` и часть агентов ядра.

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
