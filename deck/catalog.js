// Pure helpers of AIKit Deck: the command catalog from SKILL.md files, argument hints,
// the subagent list and history formatting. No mods API calls here, so tests run them directly.

export const GROUPS = [
  { id: 'dev', title: 'Разработка', skills: ['implement-feature', 'fix-bug', 'check-feature'] },
  { id: 'plan', title: 'Анализ и планирование', skills: ['analyze-mvp', 'implement-mvp', 'cross-check'] },
  { id: 'quality', title: 'Качество и безопасность', skills: ['security-check', 'coverage-check', 'tech-debt', 'write-ui-texts'] },
  { id: 'memory', title: 'Память', skills: ['capture-memory', 'memory-status', 'optimize-memory'] },
  { id: 'kit', title: 'Кит', skills: ['create-agent', 'create-skill', 'set-model', 'setup', 'improve-aikit'] },
]
export const OTHER_GROUP = { id: 'other', title: 'Прочее' }
export const PROJECT_GROUP = { id: 'project', title: 'Скиллы проекта' }

const FLAG_TOKEN = /^\[(--[\w-]+)\]$/
const RUNNING_STATUSES = new Set(['pending', 'running', 'waiting'])
const MS_PER_SECOND = 1000
const SECONDS_PER_MINUTE = 60

// Flat `key: value` frontmatter as the kit writes it; lists and nested keys are not needed here
export function parseFrontmatter(text) {
  const lines = String(text).split(/\r?\n/)
  if (lines[0] !== '---') return {}
  const fields = {}
  for (const line of lines.slice(1)) {
    if (line === '---') break
    const match = /^([\w-]+):\s*(.*)$/.exec(line)
    if (!match) continue
    let value = match[2].trim()
    if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) {
      value = value.slice(1, -1)
    }
    fields[match[1]] = value
  }
  return fields
}

// "[--tdd] [--worktree] <задача>" → toggles for the flags, a required field named "задача".
// "[путь]" → an optional field; no hint → the command runs without a field
export function parseArgumentHint(hint) {
  const flags = []
  const rest = []
  for (const token of String(hint ?? '').trim().split(/\s+(?=[[<])/)) {
    if (!token) continue
    const flag = FLAG_TOKEN.exec(token)
    if (flag) flags.push(flag[1])
    else rest.push(token)
  }
  if (rest.length === 0) return { flags, field: null }
  const text = rest.join(' ')
  const isRequired = text.startsWith('<')
  return { flags, field: { placeholder: text.replace(/^[[<]|[\]>]$/g, ''), isRequired } }
}

export function skillEntry(skill, owner, frontmatter) {
  return {
    skill,
    owner,
    description: frontmatter.description ?? '',
    argumentHint: frontmatter['argument-hint'] ?? '',
    example: frontmatter.example_prompt ?? '',
    args: parseArgumentHint(frontmatter['argument-hint']),
  }
}

export function isHidden(frontmatter) {
  return frontmatter['user-invocable'] === 'false'
}

// Skills that exist for Codex alone: the deck is a Claude Code mod, where their button is of no use
const CODEX_ONLY_SKILLS = new Set(['update-agents'])

export function isCodexOnly(name) {
  return CODEX_ONLY_SKILLS.has(name)
}

// Base skills by group, then one group per profile and per pack, then the project's own skills
// from .claude/skills/. A project skill named in GROUPS (improve-aikit in the kit repository) joins that group;
// a project copy of a kit skill (left from an attach.sh install) is skipped
export function buildGroups(baseEntries, sections, projectEntries = []) {
  const kitSkills = new Set([...baseEntries, ...sections.flatMap(section => section.entries)].map(entry => entry.skill))
  const own = projectEntries.filter(entry => !kitSkills.has(entry.skill))
  const known = [...baseEntries, ...own]
  const groups = []
  const placed = new Set()
  for (const group of GROUPS) {
    const entries = group.skills.map(skill => known.find(entry => entry.skill === skill)).filter(Boolean)
    entries.forEach(entry => placed.add(entry.skill))
    if (entries.length > 0) groups.push({ id: group.id, title: group.title, entries })
  }
  const other = baseEntries.filter(entry => !placed.has(entry.skill))
  if (other.length > 0) groups.push({ ...OTHER_GROUP, entries: other })
  for (const section of sections) {
    if (section.entries.length > 0) groups.push(section)
  }
  const rest = own.filter(entry => !placed.has(entry.skill))
  if (rest.length > 0) groups.push({ ...PROJECT_GROUP, entries: rest })
  return groups
}

// The name a command runs by: plugin skills may be namespaced ("aikit:setup")
export function resolveCommandName(entry, commands) {
  const names = commands.map(command => command.name)
  const candidates = [`${entry.owner}:${entry.skill}`, entry.skill]
  const exact = candidates.find(name => names.includes(name))
  if (exact) return exact
  return names.find(name => name.endsWith(`:${entry.skill}`)) ?? null
}

export function commandLine(name, flags, text) {
  return ['/' + name, ...flags, String(text ?? '').trim()].filter(Boolean).join(' ')
}

export function formatElapsed(ms) {
  const seconds = Math.max(0, Math.floor(ms / MS_PER_SECOND))
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE)
  return `${minutes}:${String(seconds % SECONDS_PER_MINUTE).padStart(2, '0')}`
}

export function isRunning(agent) {
  return RUNNING_STATUSES.has(agent.status)
}

// "claude-haiku-4-5-20251001" → "haiku-4-5": the family and version fit a subagent row
export function shortModel(model) {
  return String(model ?? '')
    .trim()
    .replace(/^claude-/, '')
    .replace(/-\d{8}$/, '')
}

// Running agents first (oldest on top), then the latest finished ones. The model comes from the agent list
// when the engine gives it, otherwise from the subagent's requests (models: agent id → model)
export function agentRows(agents, timing, now, finishedLimit, models = new Map()) {
  const rows = agents.map(agent => {
    const times = timing.get(agent.id) ?? { startedAt: now }
    const end = isRunning(agent) ? now : times.finishedAt ?? now
    return {
      ...agent,
      model: shortModel(agent.model ?? models.get(agent.id)),
      isRunning: isRunning(agent),
      elapsed: formatElapsed(end - times.startedAt),
      startedAt: times.startedAt,
    }
  })
  const running = rows.filter(row => row.isRunning).sort((a, b) => a.startedAt - b.startedAt)
  const finished = rows.filter(row => !row.isRunning).sort((a, b) => b.startedAt - a.startedAt).slice(0, finishedLimit)
  return [...running, ...finished]
}

// Start and finish times by agent id, kept across list refreshes
export function trackTiming(timing, agents, now) {
  for (const agent of agents) {
    const times = timing.get(agent.id)
    if (!times) {
      timing.set(agent.id, { startedAt: now, finishedAt: isRunning(agent) ? undefined : now })
    } else if (!isRunning(agent) && times.finishedAt === undefined) {
      times.finishedAt = now
    }
  }
  return timing
}

export function addHistory(history, record, limit) {
  return [record, ...history.filter(item => item.line !== record.line)].slice(0, limit)
}

export function clockTime(ms) {
  const date = new Date(ms)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

// The same limits /memory-status reports: INDEX.md holds up to 60 lines, over 50 it is time to optimize
export const MEMORY_INDEX_LIMIT = 60
export const MEMORY_INDEX_WARN = 50

export function memorySummary(indexText) {
  if (indexText === null || indexText === undefined) return { lines: null, needsOptimize: false }
  const lines = String(indexText).replace(/\n$/, '').split('\n').length
  return { lines, needsOptimize: lines > MEMORY_INDEX_WARN }
}

// The first clause of a skill's description: enough for a card under its button
export function summary(description) {
  const text = String(description ?? '').trim()
  const cut = text.search(/[.:;]\s|[.:;]$/)
  return cut > 0 ? text.slice(0, cut) : text
}

// Project actions: buttons that run a program on the machine without the model.
// A profile's own come from "actions" in its contract ({ label, argv, description }); every profile also gets
// the update of its plugin, made here from the profile name, so a new profile has it with no data of its own
export const MARKETPLACE = 'aikit'
export const ACTION_TAIL_LINES = 6
const WINDOWS_SCRIPTS = { gradlew: 'gradlew.bat' }
// cmd.exe reads these in arguments as its own syntax; an action never needs them
const CMD_SPECIAL = /[&|<>^%"]/

export function pluginUpdateSteps(plugin) {
  return [
    ['claude', 'plugin', 'marketplace', 'update', MARKETPLACE],
    ['claude', 'plugin', 'update', `${plugin}@${MARKETPLACE}`],
  ]
}

export function profileActions(profile, contractActions) {
  const own = Object.entries(contractActions && typeof contractActions === 'object' ? contractActions : {})
    .filter(([, action]) => Array.isArray(action?.argv) && action.argv.length > 0 && action.argv.every(item => typeof item === 'string' && item !== ''))
    .map(([id, action]) => ({
      id,
      label: typeof action.label === 'string' && action.label ? action.label : id,
      description: typeof action.description === 'string' ? action.description : '',
      steps: [action.argv],
      cwd: profile.root,
    }))
  const steps = pluginUpdateSteps(profile.name)
  return [
    ...own,
    { id: 'update-plugin', label: 'Обновить профиль', description: `плагин ${profile.name}@${MARKETPLACE}`, steps, cwd: '.', isUpdate: true },
  ]
}

// What the button shows: the command as written in the contract
export function actionLine(steps) {
  return steps.map(argv => argv.join(' ')).join(' && ')
}

export function isWindowsPath(path) {
  return /^[A-Za-z]:[\\/]/.test(String(path ?? '')) || String(path ?? '').startsWith('\\\\')
}

// The argv the host runs. On Windows a .bat or an npm .cmd starts only through cmd.exe, so every action goes
// through `cmd /d /c`, which also finds claude.exe or claude.cmd by PATHEXT; ./gradlew becomes gradlew.bat
export function hostArgv(argv, isWindows) {
  if (!isWindows) return { argv: [...argv] }
  const [program, ...rest] = argv
  const name = program.replace(/^\.[\\/]/, '')
  if (argv.some(item => CMD_SPECIAL.test(item))) return { error: `символы ${CMD_SPECIAL.source} в команде не запускаются через cmd.exe` }
  return { argv: ['cmd', '/d', '/c', WINDOWS_SCRIPTS[name] ?? name, ...rest] }
}

const ANSI = /\x1b\[[0-9;?]*[A-Za-z]/g

// The last lines of a running command: output comes in pieces, a line may span two of them
export function appendOutput(tail, text, limit = ACTION_TAIL_LINES) {
  const pieces = (tail.partial + String(text).replace(ANSI, '')).split(/\r\n|\n|\r/)
  const partial = pieces.pop() ?? ''
  const lines = [...tail.lines, ...pieces.filter(line => line.trim() !== '')].slice(-limit)
  return { lines, partial }
}

export function outputLines(tail, limit = ACTION_TAIL_LINES) {
  return [...tail.lines, ...(tail.partial.trim() ? [tail.partial] : [])].slice(-limit)
}

export function jobStatus(job) {
  if (!job) return ''
  if (job.status === 'running') return 'работает'
  if (job.status === 'stopped') return 'остановлено'
  if (job.status === 'error') return 'не запустилось'
  return `завершено, код ${job.code}`
}

// "2.1.299" ≥ "2.1.296": release numbers compared part by part
export function isAtLeast(version, minimum) {
  const parts = String(version ?? '').split(/[.-]/).map(Number)
  const wanted = minimum.split('.').map(Number)
  for (let i = 0; i < wanted.length; i += 1) {
    const part = Number.isFinite(parts[i]) ? parts[i] : 0
    if (part !== wanted[i]) return part > wanted[i]
  }
  return true
}
