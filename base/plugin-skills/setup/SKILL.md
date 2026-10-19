---
name: "setup"
description: "Подключить проект к AIKit, установленному плагинами: выбрать профили и паки, записать правила в CLAUDE.md или AGENTS.md, контракты .aikit/profiles.json, память и настройки команды. Используй после установки плагинов AIKit или при смене профилей проекта."
version: "1.0.0"
profile: "base"
tags: ["setup", "plugin", "onboarding"]
orchestrates: []
example_prompt: "/aikit:setup vue-nuxt+python-fastapi"
---

Подключи текущий проект к AIKit. Плагины уже дают агентов, скиллы, хуки и MCP-серверы; этот скилл записывает то, что принадлежит проекту.

## 1. Найди корень плагина

- В Claude Code корень плагина `aikit` — `${CLAUDE_PLUGIN_ROOT}`.
- В Codex переменная не подставляется: корень — папка на три уровня выше этого `SKILL.md` (`<корень>/base/plugin-skills/setup/SKILL.md`).

Проверь, что там есть `scripts/plugin-init.py`. Дальше этот путь — `<корень>`.

## 2. Выбери профили и паки

Если пользователь передал аргумент (`vue-nuxt+python-fastapi`, имя пресета или паки) — используй его.

Иначе определи стек по проекту и предложи выбор:
- профили — папки `<корень>/profiles/*`; признаки стека — `root_markers` в `profile.manifest.json` (`nuxt.config.ts`, `manage.py`, FastAPI в `pyproject.toml`);
- пресеты — `<корень>/presets/*.json` (готовые наборы профилей и паков);
- паки — `<корень>/packs/*`.

Если `.aikit/plugin-init.json` уже есть — покажи текущие профили и паки и спроси, что поменять.

## 3. Запусти подключение

Runtime — `claude` в Claude Code, `codex` в Codex.

```bash
python3 "<корень>/scripts/plugin-init.py" --runtime <claude|codex> --profiles <a+b> [--packs "quality devops"]
# или готовый набор
python3 "<корень>/scripts/plugin-init.py" --runtime <claude|codex> --preset <имя>
```

На Windows без `python3` — `python` или `py -3`.

## 4. Проверь плагины профилей

Плагины профилей и паков должны быть установлены:
- Claude Code — `/plugin install <профиль>@aikit` для каждого профиля и пака. Скрипт уже включил их в `.claude/settings.json`: участники команды получат их после доверия папке проекта.
- Codex — `codex plugin add <профиль>@aikit`. Агенты Codex скрипт записал в `.codex/agents/`.

## 5. Отчёт

```
✅ AIKit подключён

Профили:  {список}
Паки:     {список или —}
Правила:  {CLAUDE.md | AGENTS.md} — блок AIKit, остальной текст файла не тронут
Записано: .aikit/profiles.json, .aikit/memory/, PRODUCT.md{, .claude/settings.json | , .codex/agents/}

Дальше:
  1. Заполни PRODUCT.md — агенты читают его для контекста
  2. Закоммить изменения, чтобы команда получила те же настройки
  3. Перезапусти сессию, чтобы подхватились правила и агенты
```

Если скрипт напечатал предупреждение про `attach.sh` — перескажи его пользователю: копии агентов и скиллов в `.claude/` нужно удалить, иначе они дублируют плагины.
