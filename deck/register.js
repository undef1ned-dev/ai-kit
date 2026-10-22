// AIKit Deck: a pane with buttons for the kit's commands, a command reference and the session's subagents,
// plus a line under the prompt when the team memory needs /optimize-memory.
// Everything here is local: files, the command list and the subagent list. The deck never calls a model;
// a command it starts spends usage exactly as the same command typed by hand. Project actions and plugin updates
// run programs on the machine by argv, without a shell and without the model.

import {
  actionLine,
  addHistory,
  agentRows,
  appendOutput,
  buildGroups,
  clockTime,
  commandLine,
  hostArgv,
  isAtLeast,
  isCodexOnly,
  isHidden,
  isRunning,
  isWindowsPath,
  jobStatus,
  MEMORY_INDEX_LIMIT,
  memorySummary,
  outputLines,
  parseFrontmatter,
  pluginUpdateSteps,
  profileActions,
  resolveCommandName,
  skillEntry,
  summary,
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
// The project's own skills; in the kit repository — improve-aikit, run-evals, check-models
const PROJECT_SKILLS = '.claude/skills'
const PROJECT_OWNER = 'project'
// Team settings: commit 'ask' — the git-commit skill offers messages to choose, 'auto' — commits by the rules
const SETTINGS_FILE = '.aikit/settings.json'
const PROJECT_SEARCH_DEPTH = 6
const MODES = { send: 'Отправить', fill: 'Вставить' }
const RICH_UI_VERSION = '2.1.299'
const CARD_GAP = 1
const CARD_MIN_WIDTH = 24
const CARD_TWO_COLUMNS = 56
const CARD_THREE_COLUMNS = 90
const DEFAULT_COLUMNS = 60
const KIT_JOB = 'kit'
const OUTPUT_REDRAW_MS = 250
const RESTART_HINT = 'изменения подхватятся после перезапуска сессии'

let project = null
// Where the team settings live: a connected project, or a folder with .aikit/settings.json alone (the kit repository)
let team = null
let sessionRoot = ''
let groups = []
let commands = []
let agents = []
const timing = new Map()
// Subagent id → the model its last request went to, from turn.step
const agentModels = new Map()
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
let isRich = false
let wasOpenedHere = false
let isWindows = false
// Running and finished project actions and plugin updates by key; lastJob is the action whose output the deck shows
const jobs = new Map()
let lastJob = null

const redraw = $ => $.ui.invalidate('ui.render')
// A failing deck hook never holds up the event it watches
const passThrough = ($, e, next) => next(e)
const streamThrough = async function* ($, e, next) {
  return yield* next(e)
}
const historyKey = () => 'history:' + (project?.root ?? sessionRoot)
const openedKey = () => 'opened:' + (project?.root ?? sessionRoot)

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

const asSettings = value => (value && typeof value === 'object' && !Array.isArray(value) ? value : null)

// The project root is the nearest folder with .aikit/profiles.json, from the session root up;
// on the way the nearest .aikit/settings.json becomes the team settings
async function findProject($) {
  const rawRoot = String(await $.session.root())
  isWindows = isWindowsPath(rawRoot)
  sessionRoot = rawRoot.replace(/\\/g, '/')
  team = null
  let dir = sessionRoot
  for (let depth = 0; dir && depth < PROJECT_SEARCH_DEPTH; depth += 1) {
    const settings = asSettings(await readJson($, joinPath(dir, SETTINGS_FILE)))
    if (settings && !team) team = { root: dir, settings }
    const contracts = await readJson($, joinPath(dir, PROFILES_FILE))
    if (contracts && typeof contracts.profiles === 'object') {
      const init = await readJson($, joinPath(dir, INIT_FILE))
      if (!team) team = { root: dir, settings: {} }
      return {
        root: dir,
        profiles: Object.entries(contracts.profiles).map(([name, contract]) => {
          const profile = { name, label: contract?.label ?? name, root: typeof contract?.root === 'string' ? contract.root : '.' }
          return { ...profile, actions: profileActions(profile, contract?.actions) }
        }),
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
      const name = frontmatter.name || item.name
      if (!isHidden(frontmatter) && !isCodexOnly(name)) entries.push(skillEntry(name, owner, frontmatter))
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
  const own = await readSkills($, joinPath(project?.root ?? team?.root ?? sessionRoot, PROJECT_SKILLS), PROJECT_OWNER)
  groups = buildGroups(base, sections, own)
  try {
    commands = await $.command.list()
  } catch {
    commands = []
  }
  history = (await $.store.get(historyKey())) ?? []
  wasOpenedHere = Boolean(await $.store.get(openedKey()))
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
    $.ui.toast(entry.owner === PROJECT_OWNER ? `/${entry.skill} недоступна в этой сессии` : `/${entry.skill} недоступна: установите плагин ${entry.owner}@aikit`)
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

// Typography and the primary button style came in Claude Code 2.1.299; an earlier engine refuses
// a tree that sets them, so the deck draws plain bold text there
function look(ui) {
  const { Text } = ui
  const sized = (size, weight, props, text) =>
    Text(isRich ? { ...props, size, weight, children: [text] } : { ...props, ...(weight ? { bold: true } : {}), children: [text] })
  return {
    title: text => sized('title', 'bold', {}, text),
    heading: (text, props = {}) => sized('heading', 'semibold', props, text),
    label: (text, props = {}) => sized('body', 'semibold', props, text),
    caption: (text, props = {}) => sized('footnote', undefined, { dimColor: true, ...props }, text),
    variant: isActive => (isRich ? { variant: isActive ? 'primary' : 'secondary' } : {}),
  }
}

function memoryText(ui) {
  const { caption } = look(ui)
  if (memory.lines === null) return caption('память не заведена')
  const text = `память ${memory.lines}/${MEMORY_INDEX_LIMIT}`
  return memory.needsOptimize ? caption(text + ' — пора /optimize-memory', { dimColor: false, color: 'warning' }) : caption(text)
}

// Runs the steps one after another through $.process.spawn, keeping the status and the last lines of output.
// The loop over a stream is the child's life: Stop ends it, and the engine kills the child
async function runJob($, key, label, steps, cwd) {
  if (jobs.get(key)?.status === 'running') {
    $.ui.toast(`${label}: уже работает`)
    return null
  }
  const job = { label, line: actionLine(steps), status: 'running', code: null, tail: { lines: [], partial: '' }, stream: null, isStopped: false }
  jobs.set(key, job)
  if (key !== KIT_JOB) lastJob = key
  redraw($)
  let drawnAt = 0
  for (const argv of steps) {
    const prepared = hostArgv(argv, isWindows)
    if (prepared.error) {
      job.status = 'error'
      job.tail = appendOutput(job.tail, prepared.error + '\n')
      break
    }
    try {
      const stream = $.process.spawn({ argv: prepared.argv, cwd })
      job.stream = stream
      let step = await stream.next()
      while (step.done !== true && !job.isStopped) {
        job.tail = appendOutput(job.tail, step.value.text)
        const now = await $.clock.now()
        if (now - drawnAt >= OUTPUT_REDRAW_MS) {
          drawnAt = now
          redraw($)
        }
        step = await stream.next()
      }
      if (job.isStopped) break
      job.code = step.value?.code ?? null
    } catch (error) {
      if (job.isStopped) break
      job.status = 'error'
      job.tail = appendOutput(job.tail, `${argv[0]}: ${error?.message ?? error}\n`)
      break
    }
    if (job.code !== 0) break
  }
  job.stream = null
  if (job.isStopped) job.status = 'stopped'
  else if (job.status === 'running') job.status = job.code === 0 ? 'done' : 'failed'
  redraw($)
  return job
}

async function stopJob($, key) {
  const job = jobs.get(key)
  if (!job || job.status !== 'running') return
  job.isStopped = true
  redraw($)
  try {
    await job.stream?.return?.()
  } catch {
    // The child is gone already
  }
}

async function runAction($, profile, action) {
  const key = `${profile.name}:${action.id}`
  const root = project?.root ?? sessionRoot
  const job = await runJob($, key, action.label, action.steps, action.cwd === '.' ? root : joinPath(root, action.cwd))
  if (!job || !action.isUpdate) return
  $.ui.toast(job.status === 'done' ? `Профиль ${profile.name} обновлён — ${RESTART_HINT}` : `Обновление ${profile.name}: ${jobStatus(job)}`)
}

async function updateKit($) {
  const job = await runJob($, KIT_JOB, 'Обновление кита', pluginUpdateSteps($.plugin.name), project?.root ?? sessionRoot)
  if (job) $.ui.toast(job.status === 'done' ? `Кит обновлён — ${RESTART_HINT}` : `Обновление кита: ${jobStatus(job)}`)
}

function kitUpdateStatus(ui) {
  const job = jobs.get(KIT_JOB)
  const { caption } = look(ui)
  if (!job) return []
  if (job.status === 'running') return [caption('обновление…', { key: 'kit-status' })]
  if (job.status === 'done') return [caption(`кит обновлён — ${RESTART_HINT}`, { key: 'kit-status', dimColor: false, color: 'success' })]
  const last = outputLines(job.tail).pop()
  return [caption(`обновление: ${jobStatus(job)}` + (last ? ` — ${last}` : ''), { key: 'kit-status', dimColor: false, color: 'error', wrap: 'truncate-end' })]
}

function header($, ui, surface) {
  const { Box, Button } = ui
  const { title, caption, variant } = look(ui)
  const scope = project
    ? [...project.profiles.map(profile => profile.name + (profile.root === '.' ? '' : ` (${profile.root}/)`)), ...project.packs].join(' · ')
    : 'проект не подключён'
  const tabButton = (id, label, hotkey) =>
    Button({ key: 'tab-' + id, label, hotkey, ...variant(tab === id), dimColor: tab !== id, onPress: () => ((tab = id), redraw($)) })
  return Box({
    flexDirection: 'column',
    rowGap: 1,
    children: [
      Box({
        flexDirection: 'row',
        columnGap: 2,
        flexWrap: 'wrap',
        alignItems: 'flex-end',
        children: [title('AIKit Deck'), caption(scope), ...(project ? [memoryText(ui)] : [])],
      }),
      Box({
        flexDirection: 'row',
        columnGap: 1,
        flexWrap: 'wrap',
        alignItems: 'center',
        children: [
          tabButton('commands', 'Команды', '1'),
          tabButton('docs', 'Справка', '2'),
          Box({ flexGrow: 1, children: [] }),
          ...kitUpdateStatus(ui),
          Button({
            key: 'update-kit',
            label: jobs.get(KIT_JOB)?.status === 'running' ? 'Обновление…' : 'Обновить кит',
            dimColor: true,
            onPress: () => void updateKit($),
          }),
          ...(team ? [commitToggle($, ui, surface)] : []),
          Button({
            key: 'mode',
            label: `Режим: ${MODES[mode]}`,
            hotkey: 'm',
            dimColor: true,
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

// The team's commit mode lives in the repository, so the toggle writes .aikit/settings.json for everyone
function commitToggle($, ui, surface) {
  const isAuto = team.settings.commit === 'auto'
  return ui.Button({
    key: 'commit',
    label: `${isAuto ? '☑' : '☐'} Коммит без вопроса`,
    hotkey: 'c',
    ...(surface === 'terminal' ? { plain: true } : look(ui).variant(isAuto)),
    dimColor: !isAuto,
    onPress: async () => {
      const settings = { ...team.settings, commit: isAuto ? 'ask' : 'auto' }
      try {
        await $.fs.write(joinPath(team.root, SETTINGS_FILE), JSON.stringify(settings, null, 2) + '\n')
      } catch {
        $.ui.toast(`Не удалось записать ${SETTINGS_FILE}`)
        return
      }
      team.settings = settings
      redraw($)
      $.ui.toast(settings.commit === 'auto' ? 'Коммиты: сообщение по правилам, без вопроса' : 'Коммиты: сначала варианты сообщения на выбор')
    },
  })
}

function card(ui, props, children) {
  return ui.Box({ flexDirection: 'column', borderStyle: 'round', borderDimColor: true, paddingX: 1, ...props, children })
}

function agentsSection(ui, now) {
  const { Box, Text } = ui
  const { heading, caption } = look(ui)
  const rows = agentRows(agents, timing, now, FINISHED_AGENTS_SHOWN, agentModels)
  const running = rows.filter(row => row.isRunning).length
  return card(ui, { rowGap: 0 }, [
    Box({
      flexDirection: 'row',
      columnGap: 2,
      alignItems: 'flex-end',
      children: [heading('Субагенты'), caption(running > 0 ? `работают: ${running}` : 'сейчас никто не работает')],
    }),
    ...rows.map(row =>
      Box({
        key: 'agent-' + row.id,
        flexDirection: 'row',
        columnGap: 1,
        children: [
          Text({ color: row.isRunning ? 'warning' : row.status === 'completed' ? 'success' : 'error', children: [row.isRunning ? '●' : row.status === 'completed' ? '✓' : '✗'] }),
          Text({ children: [row.type] }),
          Box({ flexGrow: 1, flexShrink: 1, children: [Text({ dimColor: true, wrap: 'truncate-end', children: [row.description || row.name || ''] })] }),
          ...(row.model ? [Text({ key: 'model-' + row.id, color: 'suggestion', children: [row.model] })] : []),
          Text({ dimColor: true, children: [row.isRunning ? row.elapsed : `${row.status === 'completed' ? 'готово' : row.status} · ${row.elapsed}`] }),
        ],
      }),
    ),
  ])
}

function notConnected($, ui) {
  const { Box, Button } = ui
  const { caption } = look(ui)
  return card(ui, {}, [
    Box({
      flexDirection: 'row',
      columnGap: 1,
      flexWrap: 'wrap',
      alignItems: 'center',
      children: [
        caption('Проект не подключён: доступны базовые команды. Команды профиля появятся после', { dimColor: false }),
        Button({ key: 'setup', label: '/aikit:setup', onPress: () => press($, findEntry('setup', $.plugin.name)) }),
      ],
    }),
  ])
}

// A flag is a checkbox: ☑ when on; a terminal draws it without the button frame
function flagBox($, ui, flag, surface) {
  const isOn = flags.has(flag)
  return ui.Button({
    key: 'flag-' + flag,
    label: `${isOn ? '☑' : '☐'} ${flag}`,
    ...(surface === 'terminal' ? { plain: true } : look(ui).variant(isOn)),
    dimColor: !isOn,
    onPress: () => {
      isOn ? flags.delete(flag) : flags.add(flag)
      redraw($)
    },
  })
}

function argumentPanel($, ui, surface) {
  const { Box, Text, Button, Input } = ui
  const { heading, caption } = look(ui)
  const entry = selected
  const field = entry.args.field
  const action = mode === 'send' ? 'Запустить' : 'Вставить'
  return card(ui, { borderDimColor: false, borderColor: 'suggestion', paddingX: 2, paddingY: 1, rowGap: 1 }, [
    Box({
      flexDirection: 'row',
      columnGap: 2,
      alignItems: 'flex-end',
      children: [
        heading('/' + entry.skill, { color: 'suggestion' }),
        Box({ flexGrow: 1, flexShrink: 1, children: [caption(summary(entry.description), { wrap: 'truncate-end' })] }),
        Button({ key: 'cancel', label: 'Отмена', role: 'dismiss', dimColor: true, onPress: () => ((selected = null), redraw($)) }),
      ],
    }),
    ...(entry.args.flags.length > 0
      ? [Box({ flexDirection: 'row', columnGap: 2, flexWrap: 'wrap', children: entry.args.flags.map(flag => flagBox($, ui, flag, surface)) })]
      : []),
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
      : Box({ flexDirection: 'row', children: [Button({ key: 'run', label: action, autoFocus: true, ...look(ui).variant(true), onPress: () => submit($, entry) })] }),
    ...(fieldError ? [Text({ color: 'error', children: [fieldError] })] : []),
  ])
}

// Cards in as many columns as the pane is wide enough for
function cardWidth(columns) {
  const perRow = columns >= CARD_THREE_COLUMNS ? 3 : columns >= CARD_TWO_COLUMNS ? 2 : 1
  return Math.max(CARD_MIN_WIDTH, Math.floor((columns - CARD_GAP * (perRow - 1)) / perRow))
}

function commandCard($, ui, entry, width) {
  const { label, caption } = look(ui)
  const isAvailable = Boolean(resolveCommandName(entry, commands))
  const hasArgs = Boolean(entry.args.field) || entry.args.flags.length > 0
  return card(ui, { key: `card-${entry.owner}-${entry.skill}`, width, rowGap: 0 }, [
    ui.Button({
      key: `cmd-${entry.owner}-${entry.skill}`,
      plain: true,
      dimColor: !isAvailable,
      onPress: () => press($, entry),
      children: [label(entry.skill), ...(hasArgs ? [caption(' …')] : [])],
    }),
    caption(isAvailable ? summary(entry.description) : 'не установлена', { wrap: 'truncate-end' }),
  ])
}

function actionCard($, ui, profile, action, width) {
  const { Box, Button, Text } = ui
  const { label, caption } = look(ui)
  const key = `${profile.name}:${action.id}`
  const job = jobs.get(key)
  const isActive = job?.status === 'running'
  const mark = !job ? null : isActive ? ['●', 'warning'] : job.status === 'done' ? ['✓', 'success'] : ['✗', 'error']
  return card(ui, { key: 'action-card-' + key, width, rowGap: 0 }, [
    Box({
      flexDirection: 'row',
      columnGap: 1,
      children: [
        Button({ key: 'action-' + key, plain: true, onPress: () => void runAction($, profile, action), children: [label(action.label)] }),
        Box({ flexGrow: 1, children: [] }),
        ...(isActive ? [Button({ key: 'stop-' + key, label: 'Стоп', role: 'dismiss', dimColor: true, onPress: () => void stopJob($, key) })] : []),
      ],
    }),
    caption(actionLine(action.steps), { wrap: 'truncate-end' }),
    ...(mark ? [Text({ key: 'action-status-' + key, color: mark[1], wrap: 'truncate-end', children: [`${mark[0]} ${jobStatus(job)}`] })] : []),
  ])
}

// Buttons of the connected profiles: their own actions and the update of their plugin, then the last run's output
function actionsSection($, ui, width) {
  const { Box, Text } = ui
  const { heading, caption } = look(ui)
  const job = lastJob ? jobs.get(lastJob) : null
  const lines = job ? outputLines(job.tail) : []
  return Box({
    key: 'actions',
    flexDirection: 'column',
    rowGap: 1,
    children: [
      Box({
        flexDirection: 'row',
        columnGap: 2,
        alignItems: 'flex-end',
        children: [heading('Действия проекта'), caption('без модели: команда запускается на этой машине')],
      }),
      ...project.profiles.map(profile =>
        Box({
          key: 'actions-' + profile.name,
          flexDirection: 'column',
          rowGap: 0,
          children: [
            caption(`Профиль ${profile.name}` + (profile.root === '.' ? '' : ` · ${profile.root}/`)),
            Box({ flexDirection: 'row', flexWrap: 'wrap', columnGap: CARD_GAP, rowGap: 1, children: profile.actions.map(action => actionCard($, ui, profile, action, width)) }),
          ],
        }),
      ),
      ...(job
        ? [
            card(ui, { key: 'action-output', rowGap: 0 }, [
              caption(`${job.label} · ${job.line} · ${jobStatus(job)}`, { wrap: 'truncate-end' }),
              ...(lines.length > 0
                ? lines.map((line, index) => Text({ key: 'output-' + index, wrap: 'truncate-end', children: [line] }))
                : [caption('вывода пока нет')]),
            ]),
          ]
        : []),
    ],
  })
}

function commandsTab($, ui, columns, surface) {
  const { Box, Button } = ui
  const { heading, caption } = look(ui)
  const width = cardWidth(columns)
  return Box({
    flexDirection: 'column',
    rowGap: 2,
    children: [
      ...(project ? [] : [notConnected($, ui)]),
      ...(selected ? [argumentPanel($, ui, surface)] : []),
      ...(project ? [actionsSection($, ui, width)] : []),
      ...groups.map(group =>
        Box({
          key: 'group-' + group.id,
          flexDirection: 'column',
          rowGap: 1,
          children: [
            heading(group.title),
            Box({ flexDirection: 'row', flexWrap: 'wrap', columnGap: CARD_GAP, rowGap: 1, children: group.entries.map(entry => commandCard($, ui, entry, width)) }),
          ],
        }),
      ),
      ...(history.length > 0
        ? [
            Box({
              flexDirection: 'column',
              rowGap: 1,
              children: [
                heading('Последние запуски'),
                ...history.slice(0, HISTORY_SHOWN).map((item, index) =>
                  Button({
                    key: 'history-' + index,
                    plain: true,
                    onPress: () => repeat($, item.line),
                    children: [caption(clockTime(item.at) + '  '), item.line],
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
  const { heading, label, caption } = look(ui)
  const query = docsFilter.trim().toLowerCase()
  const matches = entry => !query || `${entry.skill} ${entry.description}`.toLowerCase().includes(query)
  return Box({
    flexDirection: 'column',
    rowGap: 2,
    children: [
      Input({
        key: 'docs-filter',
        label: 'Поиск',
        placeholder: 'имя или слово из описания',
        value: docsFilter,
        submitLabel: 'Найти',
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
            rowGap: 1,
            children: [
              heading(group.title),
              ...group.entries.map(entry =>
                card(ui, { key: `doc-${entry.owner}-${entry.skill}`, paddingY: 0 }, [
                  label(`/${resolveCommandName(entry, commands) ?? entry.skill} ${entry.argumentHint}`.trim(), { color: 'suggestion' }),
                  Text({ children: [entry.description] }),
                  ...(entry.example ? [caption('Пример: ' + entry.example)] : []),
                ]),
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
  redraw($)
  if (focus && !wasOpenedHere) {
    wasOpenedHere = true
    await $.store.set(openedKey(), true)
  }
}

// A slash command waits for the turn to end; a button in the prompt footer, beside the session's mode labels,
// opens the deck at any moment. The band above the prompt is left to other mods: it holds one tree at a time
function footerWithButton($, ui, modes) {
  return ui.Box({
    flexDirection: 'row',
    columnGap: 1,
    children: [
      ...(modes.length > 0 ? [ui.Text({ dimColor: true, children: [modes.join(' & ')] })] : []),
      ui.Button({ key: 'open-deck', label: 'AIKit Deck', plain: true, onPress: () => openPane($, true) }),
    ],
  })
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    mode = (await $.store.get('mode')) === 'fill' ? 'fill' : 'send'
    try {
      const engine = await $.session.version()
      isRich = isAtLeast(engine.base ?? engine.version, RICH_UI_VERSION)
    } catch {
      isRich = false
    }
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
    // Opens by itself where the deck belongs: a connected project, team settings alone (the kit repository)
    // or a folder where the deck was opened before
    if (project || team || wasOpenedHere) await openPane($, false)
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
    if (e.id === PANE) {
      isPaneOpen = false
      redraw($)
    }
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

  // A subagent's request names its model: the one the API answered with, or the one it was sent to.
  // The hook only reads the request and passes it on unchanged
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    const model = result?.usage?.model ?? e.model
    if (e.agentId && model && agentModels.get(e.agentId) !== model) {
      agentModels.set(e.agentId, model)
      redraw($)
    }
    return result
  }).catch(streamThrough)

  // A background subagent reports its end with a task notification
  on('session.receive', async ($, e, next) => {
    const result = await next(e)
    if (e.origin?.kind === 'task-notification') await refreshAgents($)
    return result
  }).catch(passThrough)

  // Shown while the deck is closed, in a connected project or one where the deck was opened before
  on('ui.render', { component: 'SessionMode' }, ($, e, next) => {
    if (isPaneOpen || !(project || wasOpenedHere)) return next(e)
    return footerWithButton($, $.ui.resolve(e), e.props.modes)
  }).catch(passThrough)

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    isPaneOpen = true
    const ui = $.ui.resolve(e)
    const now = await $.clock.now()
    const columns = Math.max(CARD_MIN_WIDTH, (e.props?.bodyColumns ?? DEFAULT_COLUMNS) - 2)
    return ui.Box({
      flexDirection: 'column',
      rowGap: 2,
      paddingX: 1,
      paddingY: 1,
      children: [header($, ui, e.surface), agentsSection(ui, now), tab === 'docs' ? docsTab($, ui) : commandsTab($, ui, columns, e.surface)],
    })
  })
}
