---
name: "set-model"
description: "Сменить модель агента AIKit в проекте: уровень (opus, sonnet, haiku) или конкретную модель для Claude Code, Codex или OpenCode. Записывает .aikit/models.json — общий для команды, хранится в git. Используй, когда пользователь просит поставить агенту другую модель или показать, какие модели у агентов."
argument-hint: "[агент] [opus|sonnet|haiku|модель] [--runtime claude|codex|opencode]"
disable-model-invocation: true
version: "1.0.0"
profile: "base"
tags: ["models", "agents", "settings"]
orchestrates: []
example_prompt: "/set-model security-auditor sonnet"
---

Смени модель агента AIKit в этом проекте.

$ARGUMENTS

## 1. Найди кит

Корень кита — первое, что существует:
- `${CLAUDE_PLUGIN_ROOT}` в Claude Code с установкой плагинами;
- `.aikit-config/` в проекте (установка `attach.sh` или адаптером);
- в Codex с установкой плагинами — папка на три уровня выше этого `SKILL.md` (`<корень>/base/skills/set-model/SKILL.md`).

В корне должны быть `scripts/agent_models.py` и `adapters/models.json`. Дальше этот путь — `<корень>`.

## 2. Без аргументов — покажи модели

Прочитай `<корень>/adapters/models.json` (уровни и модели каждого runtime) и `.aikit/models.json` проекта, если он есть. Покажи таблицу: агенты из `.aikit/profiles.json` (роли и специалисты) и агенты ядра, их уровень из описания агента, переопределение проекта и итоговую модель в текущем runtime. Для Codex и OpenCode можно взять готовое: `python3 <корень>/scripts/agent_models.py show --runtime <runtime> --workspace .`.

Объясни коротко: `opus` — самые сложные решения (архитектура, ревью, безопасность), `sonnet` — основная работа, `haiku` — простые и частые задачи. Чем выше уровень, тем больше расход лимитов.

## 3. С аргументами — запиши переопределение

1. Проверь агента: он есть среди агентов кита (`<корень>/base/agents`, `<корень>/profiles/*/agents`, `<корень>/packs/*/agents`). Опечатка — предложи похожие имена.
2. Проверь модель:
   - уровень (`opus`, `sonnet`, `haiku`) — подходит для любого runtime;
   - конкретная модель — нужен runtime (`--runtime` или текущий). Модели Claude — алиас или id (`claude-opus-5-5`), Codex — id модели OpenAI, OpenCode — `provider/model`. Сомневаешься, что модель существует, — сверься с источниками из `adapters/models.json` и скажи пользователю.
3. Запиши в `.aikit/models.json` (создай, если нет), остальное содержимое сохрани:
   - уровень: `"agents": {"<агент>": "<уровень>"}`;
   - модель для runtime: `"agents": {"<агент>": {"<runtime>": "<модель>"}}` — объект дополняется, другие runtime не трогай;
   - вернуть модель по умолчанию — удали запись агента.

## 4. Примени

- **Claude Code, установка плагинами** — файлы агентов в плагине, их не меняем. Модель передаётся параметром `model` при запуске агента по правилу из `CLAUDE.md`; действует с этой же сессии.
- **Claude Code через `attach.sh`** (агенты в `.claude/agents/`), **Codex** (`.codex/agents/`), **OpenCode** (`.opencode/agents/`) — запиши модель в файлы агентов:
  ```bash
  python3 <корень>/scripts/agent_models.py apply --runtime <claude|codex|opencode> --workspace .
  ```
  На Windows без `python3` — `python` или `py -3`. Codex и OpenCode подхватят изменения в новой сессии. Обновление кита (`update.sh`, адаптер, `/aikit:setup`) применяет `.aikit/models.json` заново.

## 5. Отчёт

```
✅ Модель агента изменена

Агент:    <агент>
Было:     <уровень или модель>
Стало:    <уровень или модель> (<runtime или «все runtime»>)
Записано: .aikit/models.json — закоммить, чтобы команда получила ту же настройку
```
