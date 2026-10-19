// AIKit Deck: a pane with buttons for the kit's commands, a command reference and the session's subagents,
// plus a line under the prompt when the team memory needs /optimize-memory.
// Everything here is local: files, the command list and the subagent list. The deck never calls a model;
// a command it starts spends usage exactly as the same command typed by hand.

import {
  addHistory,
  agentRows,
  buildGroups,
  clockTime,
  commandLine,
  isHidden,
  isRunning,
  MEMORY_INDEX_LIMIT,
  memorySummary,
  parseFrontmatter,
  resolveCommandName,
  skillEntry,
  trackTiming,
} from './catalog.js'

const PANE = 'aikit-deck'
const COMMAND = 'deck'
const AGENT_TOOLS = ['Agent', 'Task']
const AGENT_POLL_MS = 2000
const FINISHED_AGENTS_SHOWN = 3
const HISTORY_LIMIT = 20
const HISTORY_SHOWN = 5
const PROFILES_FILE = '.aikit/profiles.json'
const INIT_FILE = '.aikit/plugin-init.json'
const MEMORY_INDEX = '.aikit/memory/INDEX.md'
const PROJECT_SEARCH_DEPTH = 6
const MODES = { send: 'Отправить', fill: 'Вставить' }

let project = null
let sessionRoot = ''
let groups = []
let commands = []
let agents = []
const timing = new Map()
let history = []
let mode = 'send'
let tab = 'commands'
let selected = null
let argText = ''
let flags = new Set()
let fieldError = ''
let docsFilter = ''
let isPaneOpen = false
let memory = memorySummary(null)

const redraw = $ => $.ui.invalidate('ui.render')
// A failing deck hook never holds up the event it watches
const passThrough = ($, e, next) => next(e)
const historyKey = () => 'history:' + (project?.root ?? sessionRoot)

function joinPath(...parts) {
  return parts.join('/').replace(/\\/g, '/').replace(/\/+/g, '/')
}

function parentOf(path) {
  const trimmed = path.replace(/\/+$/, '')
  const cut = trimmed.lastIndexOf('/')
  return cut > 0 ? trimmed.slice(0, cut) : null
}

async function readJson($, path) {
  try {
    return JSON.parse(await $.fs.read(path))
  } catch {
    return null
  }
}

// The project root is the nearest folder with .aikit/profiles.json, from the session root up
async function findProject($) {
  sessionRoot = String(await $.session.root()).replace(/\\/g, '/')
  let dir = sessionRoot
  for (let depth = 0; dir && depth < PROJECT_SEARCH_DEPTH; depth += 1) {
    const contracts = await readJson($, joinPath(dir, PROFILES_FILE))
    if (contracts && typeof contracts.profiles === 'object') {
      const init = await readJson($, joinPath(dir, INIT_FILE))
      return {
        root: dir,
        profiles: Object.entries(contracts.profiles).map(([name, contract]) => ({
          name,
          label: contract?.label ?? name,
          root: typeof contract?.root === 'string' ? contract.root : '.',
        })),
        packs: Array.isArray(init?.packs) ? init.packs.filter(name => typeof name === 'string') : [],
      }
    }
    dir = parentOf(dir)
  }
  return null
}

// The kit sources: the core plugin's root is the repository root, with base/, profiles/ and packs/
async function kitRoot($) {
  const root = String($.plugin.root).replace(/\\/g, '/')
  for (const candidate of [root, parentOf(root)]) {
    if (candidate && (await $.fs.exists(joinPath(candidate, 'base/skills')))) return candidate
  }
  return root
}

async function readSkills($, dir, owner) {
  let listing = []
  try {
    listing = await $.fs.list(dir)
  } catch {
    return []
  }
  const entries = []
  for (const item of [...listing].sort((a, b) => a.name.localeCompare(b.name))) {
    if (item.kind !== 'dir') continue
    try {
      const frontmatter = parseFrontmatter(await $.fs.read(joinPath(dir, item.name, 'SKILL.md')))
      if (!isHidden(frontmatter)) entries.push(skillEntry(frontmatter.name || item.name, owner, frontmatter))
    } catch {
      // A folder without SKILL.md is not a skill
    }
  }
  return entries
}

async function loadCatalog($) {
  project = await findProject($)
  const kit = await kitRoot($)
  const base = [
    ...(await readSkills($, joinPath(kit, 'base/skills'), $.plugin.name)),
    ...(await readSkills($, joinPath(kit, 'base/plugin-skills'), $.plugin.name)),
  ]
  const sections = []
  for (const profile of project?.profiles ?? []) {
    sections.push({
      id: 'profile-' + profile.name,
      title: `Профиль ${profile.name}` + (profile.root === '.' ? '' : ` · ${profile.root}/`),
      entries: await readSkills($, joinPath(kit, 'profiles', profile.name, 'skills'), profile.name),
    })
  }
  for (const pack of project?.packs ?? []) {
    sections.push({ id: 'pack-' + pack, title: `Пак ${pack}`, entries: await readSkills($, joinPath(kit, 'packs', pack, 'skills'), pack) })
  }
  groups = buildGroups(base, sections)
  try {
    commands = await $.command.list()
  } catch {
    commands = []
  }
  history = (await $.store.get(historyKey())) ?? []
}

async function refreshMemory($) {
  let index = null
  if (project) {
    try {
      index = await $.fs.read(joinPath(project.root, MEMORY_INDEX))
    } catch {
      index = null
    }
  }
  const summary = memorySummary(index)
  if (summary.lines === memory.lines && summary.needsOptimize === memory.needsOptimize) return
  memory = summary
  $.ui.status(memory.needsOptimize ? `память: INDEX ${memory.lines}/${MEMORY_INDEX_LIMIT} строк — пора /optimize-memory` : undefined)
  redraw($)
}

async function refreshAgents($) {
  try {
    agents = await $.agent.list()
  } catch {
    return
  }
  trackTiming(timing, agents, await $.clock.now())
  redraw($)
}

function findEntry(skill, owner) {
  for (const group of groups) {
    const entry = group.entries.find(item => item.skill === skill && item.owner === owner)
    if (entry) return entry
  }
  return null
}

function select($, entry, text = '') {
  selected = entry
  argText = text
  flags = new Set()
  fieldError = ''
  redraw($)
}

async function remember($, line, source) {
  history = addHistory(history, { line, source, at: await $.clock.now() }, HISTORY_LIMIT)
  redraw($)
  await $.store.set(historyKey(), history)
}

async function launch($, entry, text) {
  const name = resolveCommandName(entry, commands)
  if (!name) {
    $.ui.toast(`/${entry.skill} недоступна: установите плагин ${entry.owner}@aikit`)
    return
  }
  const args = [...flags, String(text ?? '').trim()].filter(Boolean).join(' ')
  const line = commandLine(name, [...flags], text)
  if (mode === 'fill') {
    const filled = await $.prompt.fill({ text: line + ' ' })
    if (!filled?.isFilled) {
      $.ui.toast('Поле ввода сейчас недоступно')
      return
    }
  } else {
    $.command.run({ command: name, args }).catch(error => $.ui.toast(`${line}: ${error.message}`))
  }
  selected = null
  argText = ''
  flags = new Set()
  await remember($, line, 'deck')
}

function submit($, entry) {
  const field = entry.args.field
  if (field?.isRequired && !argText.trim()) {
    fieldError = `Заполните: ${field.placeholder}`
    redraw($)
    return
  }
  return launch($, entry, argText)
}

function press($, entry) {
  if (!entry.args.field && entry.args.flags.length === 0) return launch($, entry, '')
  select($, entry)
}

function memoryText(ui) {
  const { Text } = ui
  if (memory.lines === null) return Text({ dimColor: true, children: ['· память не заведена'] })
  const text = `· память ${memory.lines}/${MEMORY_INDEX_LIMIT}`
  return memory.needsOptimize ? Text({ color: 'warning', children: [text + ' — пора /optimize-memory'] }) : Text({ dimColor: true, children: [text] })
}

function header($, ui) {
  const { Box, Text, Button } = ui
  const scope = project
    ? [...project.profiles.map(profile => profile.name + (profile.root === '.' ? '' : ` (${profile.root}/)`)), ...project.packs].join(' · ')
    : 'проект не подключён'
  return Box({
    flexDirection: 'column',
    children: [
      Box({
        flexDirection: 'row',
        columnGap: 1,
        flexWrap: 'wrap',
        children: [
          Text({ bold: true, children: ['AIKit Deck'] }),
          Text({ dimColor: true, children: [scope] }),
          ...(project ? [memoryText(ui)] : []),
        ],
      }),
      Box({
        flexDirection: 'row',
        columnGap: 2,
        flexWrap: 'wrap',
        children: [
          Button({ key: 'tab-commands', label: 'Команды', hotkey: '1', plain: true, dimColor: tab !== 'commands', onPress: () => ((tab = 'commands'), redraw($)) }),
          Button({ key: 'tab-docs', label: 'Справка', hotkey: '2', plain: true, dimColor: tab !== 'docs', onPress: () => ((tab = 'docs'), redraw($)) }),
          Button({
            key: 'mode',
            label: `Режим: ${MODES[mode]}`,
            hotkey: 'm',
            plain: true,
            onPress: async () => {
              mode = mode === 'send' ? 'fill' : 'send'
              redraw($)
              await $.store.set('mode', mode)
            },
          }),
        ],
      }),
    ],
  })
}

function agentsSection(ui, now) {
  const { Box, Text } = ui
  const rows = agentRows(agents, timing, now, FINISHED_AGENTS_SHOWN)
  const running = rows.filter(row => row.isRunning).length
  const title = running > 0 ? `Субагенты · работают: ${running}` : 'Субагенты · сейчас никто не работает'
  return Box({
    flexDirection: 'column',
    marginTop: 1,
    children: [
      Text({ dimColor: true, children: [title] }),
      ...rows.map(row =>
        Box({
          key: 'agent-' + row.id,
          flexDirection: 'row',
          columnGap: 1,
          children: [
            Text({ color: row.isRunning ? 'warning' : row.status === 'completed' ? 'success' : 'error', children: [row.isRunning ? '●' : row.status === 'completed' ? '✓' : '✗'] }),
            Text({ children: [row.type] }),
            Text({ dimColor: true, wrap: 'truncate-end', children: [row.description || row.name || ''] }),
            Text({ dimColor: true, children: [row.isRunning ? row.elapsed : `${row.status === 'completed' ? 'готово' : row.status} · ${row.elapsed}`] }),
          ],
        }),
      ),
    ],
  })
}

function argumentPanel($, ui) {
  const { Box, Text, Button, Input } = ui
  const entry = selected
  const field = entry.args.field
  const action = mode === 'send' ? 'запустить' : 'вставить'
  return Box({
    flexDirection: 'column',
    marginTop: 1,
    borderStyle: 'round',
    paddingX: 1,
    children: [
      Box({
        flexDirection: 'row',
        columnGap: 2,
        flexWrap: 'wrap',
        children: [
          Text({ color: 'suggestion', children: ['/' + entry.skill] }),
          ...entry.args.flags.map(flag =>
            Button({
              key: 'flag-' + flag,
              label: (flags.has(flag) ? '[x] ' : '[ ] ') + flag,
              plain: true,
              onPress: () => {
                flags.has(flag) ? flags.delete(flag) : flags.add(flag)
                redraw($)
              },
            }),
          ),
          Button({ key: 'cancel', label: 'отмена', plain: true, dimColor: true, onPress: () => ((selected = null), redraw($)) }),
        ],
      }),
      field
        ? Input({
            key: 'arg',
            label: field.isRequired ? field.placeholder : `${field.placeholder} (необязательно)`,
            placeholder: entry.example.replace(/^\/?[\w:-]+\s*/, '') || field.placeholder,
            value: argText,
            submitLabel: action,
            autoFocus: true,
            onInput: value => {
              argText = value
              fieldError = ''
            },
            onSubmit: value => {
              argText = value
              return submit($, entry)
            },
          })
        : Button({ key: 'run', label: action, autoFocus: true, onPress: () => submit($, entry) }),
      ...(fieldError ? [Text({ color: 'error', children: [fieldError] })] : []),
    ],
  })
}

// Base commands work without a profile; /setup adds the profile's commands and contracts
function notConnected($, ui) {
  const { Box, Text, Button } = ui
  return Box({
    flexDirection: 'row',
    columnGap: 1,
    flexWrap: 'wrap',
    marginTop: 1,
    children: [
      Text({ dimColor: true, children: ['Проект не подключён: доступны базовые команды, команды профиля появятся после'] }),
      Button({ key: 'setup', label: '/aikit:setup', plain: true, onPress: () => press($, findEntry('setup', $.plugin.name)) }),
    ],
  })
}

function commandsTab($, ui) {
  const { Box, Text, Button } = ui
  return Box({
    flexDirection: 'column',
    children: [
      ...(project ? [] : [notConnected($, ui)]),
      ...(selected ? [argumentPanel($, ui)] : []),
      ...groups.map(group =>
        Box({
          key: 'group-' + group.id,
          flexDirection: 'column',
          marginTop: 1,
          children: [
            Text({ dimColor: true, children: [group.title] }),
            Box({
              flexDirection: 'row',
              flexWrap: 'wrap',
              columnGap: 1,
              children: group.entries.map(entry =>
                Button({
                  key: `cmd-${entry.owner}-${entry.skill}`,
                  label: entry.skill + (entry.args.field || entry.args.flags.length > 0 ? ' …' : ''),
                  dimColor: !resolveCommandName(entry, commands),
                  onPress: () => press($, entry),
                }),
              ),
            }),
          ],
        }),
      ),
      ...(history.length > 0
        ? [
            Box({
              flexDirection: 'column',
              marginTop: 1,
              children: [
                Text({ dimColor: true, children: ['Последние запуски'] }),
                ...history.slice(0, HISTORY_SHOWN).map((item, index) =>
                  Button({
                    key: 'history-' + index,
                    label: `${clockTime(item.at)}  ${item.line}`,
                    plain: true,
                    dimColor: true,
                    onPress: () => repeat($, item.line),
                  }),
                ),
              ],
            }),
          ]
        : []),
    ],
  })
}

// A history row opens its command again with the same text, ready to edit
function repeat($, line) {
  const [head, ...rest] = line.replace(/^\//, '').split(' ')
  const skill = head.split(':').pop()
  for (const group of groups) {
    const entry = group.entries.find(item => item.skill === skill)
    if (!entry) continue
    const words = rest.filter(word => !entry.args.flags.includes(word))
    select($, entry, words.join(' '))
    rest.filter(word => entry.args.flags.includes(word)).forEach(flag => flags.add(flag))
    return
  }
}

function docsTab($, ui) {
  const { Box, Text, Input } = ui
  const query = docsFilter.trim().toLowerCase()
  const matches = entry => !query || `${entry.skill} ${entry.description}`.toLowerCase().includes(query)
  return Box({
    flexDirection: 'column',
    marginTop: 1,
    children: [
      Input({
        key: 'docs-filter',
        label: 'Поиск',
        placeholder: 'имя или слово из описания',
        value: docsFilter,
        submitLabel: 'найти',
        onInput: value => ((docsFilter = value), redraw($)),
        onSubmit: value => ((docsFilter = value), redraw($)),
      }),
      ...groups
        .map(group => ({ ...group, entries: group.entries.filter(matches) }))
        .filter(group => group.entries.length > 0)
        .map(group =>
          Box({
            key: 'docs-' + group.id,
            flexDirection: 'column',
            marginTop: 1,
            children: [
              Text({ bold: true, children: [group.title] }),
              ...group.entries.map(entry =>
                Box({
                  key: `doc-${entry.owner}-${entry.skill}`,
                  flexDirection: 'column',
                  marginTop: 1,
                  children: [
                    Text({ color: 'suggestion', children: [`/${resolveCommandName(entry, commands) ?? entry.skill} ${entry.argumentHint}`.trim()] }),
                    Text({ children: [entry.description] }),
                    ...(entry.example ? [Text({ dimColor: true, children: ['Пример: ' + entry.example] })] : []),
                  ],
                }),
              ),
            ],
          }),
        ),
    ],
  })
}

async function openPane($, focus) {
  const pane = { id: PANE, title: 'AIKit Deck', closeOnEscape: true }
  const opened = await $.ui.open(focus ? { ...pane, focus: true } : pane)
  isPaneOpen = Boolean(opened?.isPlaced) || focus
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    mode = (await $.store.get('mode')) === 'fill' ? 'fill' : 'send'
    await loadCatalog($)
    await refreshMemory($)
    await refreshAgents($)
    $.clock.every(AGENT_POLL_MS, async () => {
      if (isPaneOpen && agents.some(isRunning)) await refreshAgents($)
    })
    await $.command.register({
      name: COMMAND,
      description: 'AIKit Deck: кнопки команд кита, справка и субагенты сессии',
      immediate: true,
    })
    if (project) await openPane($, false)
    return next(e)
  })

  on('command.run', { command: COMMAND }, async $ => {
    await loadCatalog($)
    await refreshMemory($)
    await refreshAgents($)
    await openPane($, true)
    return {}
  }).catch(passThrough)

  // Commands typed in the chat go to the history too
  on('command.run', async ($, e, next) => {
    const skill = e.command.split(':').pop()
    if (e.command !== COMMAND && groups.some(group => group.entries.some(entry => entry.skill === skill))) {
      await remember($, commandLine(e.command, [], e.args), 'chat')
    }
    return next(e)
  }).catch(passThrough)

  // /capture-memory and /optimize-memory change INDEX.md during a turn
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    await refreshMemory($)
    return result
  }).catch(passThrough)

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) isPaneOpen = false
    return next(e)
  }).catch(passThrough)

  // Subagents started from the chat, a skill or the deck: the list comes from Claude Code itself
  on('agent.spawn', async ($, e, next) => {
    const started = await next(e)
    await refreshAgents($)
    return started
  }).catch(passThrough)

  on('tool.call', { tool: AGENT_TOOLS }, async ($, e, next) => {
    const result = await next(e)
    await refreshAgents($)
    return result
  }).catch(passThrough)

  // A background subagent reports its end with a task notification
  on('session.receive', async ($, e, next) => {
    const result = await next(e)
    if (e.origin?.kind === 'task-notification') await refreshAgents($)
    return result
  }).catch(passThrough)

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    isPaneOpen = true
    const ui = $.ui.resolve(e)
    const now = await $.clock.now()
    return ui.Box({
      flexDirection: 'column',
      children: [header($, ui), agentsSection(ui, now), tab === 'docs' ? docsTab($, ui) : commandsTab($, ui)],
    })
  })
}
