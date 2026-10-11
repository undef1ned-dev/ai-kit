# Adapter Runtime Execution

Этот документ фиксирует execution layer для non-Claude adapters AIKit.

Его цель:
- сделать runtime install flow не только упаковкой файлов, но и воспроизводимым execution contract;
- описать, где runtime должен искать guide, continuation prompt и packaged maintainer surface;
- дать единый source of truth для Codex, GLM и OpenCode workspaces.

---

## Source of truth

- `adapters/*/adapter.manifest.json`
- `.aikit/runtime-entrypoints.json` внутри build/install output
- `.aikit/runtime-graph.json` внутри build/install output
- `.aikit/runtime-operating-protocol.md` внутри build/install output
- `.aikit/runtime-continuation-contract.md` внутри build/install output
- `.aikit/runtime-tools.json` внутри build/install output
- `.aikit/mcp-tool-plane.json` внутри build/install output
- `entrypoints.json` внутри runtime config root, если adapter использует directory-based config root
- `runtime-graph.json` внутри runtime config root, если adapter публикует runtime-local graph surface

---

## Что такое runtime entrypoint

`runtime_entrypoints` в adapter manifest описывает:
- `name` — стабильное имя entrypoint
- `path` — generated artifact, который runtime должен открыть или использовать
- `kind` — тип entrypoint (`guide`, `continuation`, `agent-entry`, `command-surface`, ...)
- `purpose` — зачем этот entrypoint нужен человеку или runtime

Это не замена routing и не замена workflow policy.
Это execution bridge между:
- установленным runtime workspace;
- packaged AIKit surface;
- следующим реальным действием пользователя или другого runtime.

---

## Current contract

### Codex
- `.codex/AIKIT.md` — runtime guide
- `.codex/CONTINUE_AIKIT_MAINTAINER.md` — maintainer continuation prompt
- `.codex/agents/*.toml` — native custom-agent registration surface
- `.codex/skills/*/SKILL.md` — native skill surface
- `.codex/commands/` — compatibility-only command aliases for `/aikit-runtime-workspace`, `/aikit-bootstrap-project` and maintainer surfaces
- `.aikit/agents/` — packaged maintainer agent surface
- `/aikit-runtime-workspace` — user-facing lifecycle command for install/update, command surface sync and bootstrap

### GLM
- `.glm/AIKIT.md` — runtime guide
- `.glm/CONTINUE_AIKIT_MAINTAINER.md` — maintainer continuation prompt
- `.aikit/agents/` — packaged maintainer agent surface

### OpenCode
- `.opencode/AIKIT.md` — runtime guide
- `.opencode/CONTINUE_AIKIT_MAINTAINER.md` — maintainer continuation prompt
- `.aikit/agents/` — packaged maintainer agent surface

### Claude
- `CLAUDE.md` — primary runtime guide
- `.claude/commands/` — slash-command surface
- `.claude/agents/` — runtime agent surface
- `.claude/settings.json` — merged Claude Code settings surface for the selected profiles and packs
- `.claude/.config-version` — installed profile/pack/version marker for update flow

Claude capability parity rule:
- capability set should stay aligned with Codex;
- the same shared skills are exposed as `.claude/commands/*.md` in Claude and `.codex/skills/*/SKILL.md` in Codex;
- the same shared agents are exposed as `.claude/agents/*.md` in Claude and `.codex/agents/*.toml` plus canonical markdown mirrors in Codex.

---

## Generated artifacts

Для runtime adapters после build/install ожидаются:
- `.aikit/runtime-entrypoints.json`
- `.aikit/runtime-graph.json`
- `.aikit/runtime-operating-protocol.md`
- `.aikit/runtime-continuation-contract.md`
- `.aikit/runtime-tools.json`
- `.aikit/mcp-tool-plane.json`
- runtime-specific `entrypoints.json` внутри config root, например `.codex/entrypoints.json`
- runtime-specific `runtime-graph.json` внутри config root, например `.codex/runtime-graph.json`
- `.aikit/INSTALL.md`

Это даёт три уровня:
1. bundled core
2. runtime-specific launcher files
3. structured execution contract
4. packaged workflow DAG surface для runtime exploration
5. MCP/provider tool plane для runtime-native внешних инструментов

---

## Install vs Update

Для active workspace-sync adapters `install` и `update` разделены явно:
- `/aikit-runtime-workspace <adapter> --preset <preset> --workspace <path>` является основным пользовательским lifecycle path;
- `scripts/run-runtime-workspace.py` является internal runner для slash command и вызывает install/update/bootstrap под капотом;
- `scripts/install-adapter-package.py` создаёт runtime workspace с нуля или поверх пустой директории;
- `scripts/update-adapter-package.py` пересинхронизирует уже установленный workspace и пишет `.aikit/UPDATE.md`;
- оба сценария должны сохранять валидные runtime entrypoints, continuation prompt и packaged agent surface.

---

## Why this matters

До этого install flow говорил только “workspace установлен”.
Теперь runtime workspace ещё и явно объясняет:
- где стартовать работу;
- чем continuation отличается от runtime guide;
- какой packaged agent является canonical точкой входа для развития самого AIKit.
- что Python scripts являются internal tooling layer для CLI-агента, а не основным интерфейсом пользователя.
- какие internal tools доступны агенту в machine-readable формате.
- какие MCP/provider tools доступны через runtime-native layer и почему их нельзя запускать как shell commands.
- как resumed flow, bundle handoff и lineage должны одинаково работать в Codex / GLM / OpenCode.
- как `/aikit-runtime-workspace` объединяет install/update, command surface sync и `/aikit-bootstrap-project` handoff в один user-facing lifecycle route.
