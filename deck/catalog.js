// Pure helpers of AIKit Deck: the command catalog from SKILL.md files, argument hints,
// the subagent list and history formatting. No mods API calls here, so tests run them directly.

export const GROUPS = [
  { id: 'dev', title: 'Разработка', skills: ['implement-feature', 'fix-bug', 'check-feature', 'workflow'] },
  { id: 'plan', title: 'Анализ и планирование', skills: ['analyze-mvp', 'implement-mvp', 'cross-check'] },
  { id: 'quality', title: 'Качество и безопасность', skills: ['security-check', 'coverage-check', 'tech-debt', 'write-ui-texts'] },
  { id: 'memory', title: 'Память', skills: ['capture-memory', 'memory-status', 'optimize-memory'] },
  { id: 'kit', title: 'Кит', skills: ['create-agent', 'create-skill', 'improve-aikit', 'setup'] },
]
export const OTHER_GROUP = { id: 'other', title: 'Прочее' }

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

// Base skills by group, then one group per profile and per pack of the project
export function buildGroups(baseEntries, sections) {
  const groups = []
  const placed = new Set()
  for (const group of GROUPS) {
    const entries = group.skills.map(skill => baseEntries.find(entry => entry.skill === skill)).filter(Boolean)
    entries.forEach(entry => placed.add(entry.skill))
    if (entries.length > 0) groups.push({ id: group.id, title: group.title, entries })
  }
  const other = baseEntries.filter(entry => !placed.has(entry.skill))
  if (other.length > 0) groups.push({ ...OTHER_GROUP, entries: other })
  for (const section of sections) {
    if (section.entries.length > 0) groups.push(section)
  }
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

// Running agents first (oldest on top), then the latest finished ones
export function agentRows(agents, timing, now, finishedLimit) {
  const rows = agents.map(agent => {
    const times = timing.get(agent.id) ?? { startedAt: now }
    const end = isRunning(agent) ? now : times.finishedAt ?? now
    return { ...agent, isRunning: isRunning(agent), elapsed: formatElapsed(end - times.startedAt), startedAt: times.startedAt }
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
