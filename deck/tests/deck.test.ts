import { expect, mock, test } from 'claude-code/testing'

import {
  actionLine,
  agentRows,
  appendOutput,
  hostArgv,
  installedVersion,
  isAtLeast,
  isWindowsPath,
  memorySummary,
  newestVersion,
  outputLines,
  parseArgumentHint,
  parseFrontmatter,
  pluginsDir,
  pluginUpdateSteps,
  profileActions,
  resolveCommandName,
  shortModel,
  summary,
  trackTiming,
  updateRecords,
  updateToast,
} from '../catalog.js'

const PROJECT = '/work/shop'
const PROFILES = JSON.stringify({ profiles: { 'vue-nuxt': { label: 'Vue Nuxt', root: 'web' } } })
const JAVA_ACTIONS = {
  compileJava: { label: 'Компиляция', argv: ['./gradlew', 'compileJava'], description: 'Компиляция мода' },
  runClient: { label: 'Клиент', argv: ['./gradlew', 'runClient'] },
}
const JAVA_PROFILES = JSON.stringify({ profiles: { 'forge-1-12-java': { label: 'Forge', root: '.', actions: JAVA_ACTIONS } } })
const SKILLS: Record<string, string> = {
  'base/skills/implement-feature': 'argument-hint: "[--tdd] [--worktree] <задача>"\nexample_prompt: "/implement-feature страница заказов"',
  'base/skills/memory-status': 'example_prompt: "/memory-status"',
  'base/skills/git-commit': 'user-invocable: false',
  'base/plugin-skills/setup': 'argument-hint: "[профили или пресет]"',
  'base/plugin-skills/update-agents': 'example_prompt: "$aikit:update-agents"',
  'profiles/vue-nuxt/skills/new-page': 'argument-hint: "<маршрут>"',
  // The project's own skills: the kit repository's improve-aikit and run-evals, a leftover copy of a kit skill
  '.claude/skills/improve-aikit': 'argument-hint: "<что изменить в ките>"',
  '.claude/skills/run-evals': 'argument-hint: "[профиль]"',
  '.claude/skills/implement-feature': 'argument-hint: "<задача>"',
}
const COMMANDS = [
  { name: 'implement-feature', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'memory-status', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'aikit:setup', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'new-page', description: '', source: 'plugin', plugin: 'vue-nuxt' },
  { name: 'improve-aikit', description: '', source: 'project' },
  { name: 'run-evals', description: '', source: 'project' },
]
const PANE = {
  plugin: 'aikit',
  component: 'Pane',
  requestId: 'aikit-deck',
  viewport: { columns: 120, rows: 40 },
  props: { title: 'AIKit Deck', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const
const FOOTER = {
  plugin: 'aikit',
  component: 'SessionMode',
  requestId: 'session-mode',
  viewport: { columns: 120, rows: 40 },
  props: { modes: ['focus'] },
} as const
const BAND = {
  plugin: 'aikit',
  component: 'AbovePrompt',
  requestId: 'above-prompt',
  viewport: { columns: 120, rows: 40 },
  props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 118, scroll: { offset: 0, bodyRows: 10 }, view: {} },
} as const
// What the engine answers an open the deck makes itself in a terminal narrower than its threshold
const UNASKED_REASON = 'unasked below 144 columns (120 now): placed when the person opens it, or when the terminal is widened to 144 columns'

// The engine hands paths in the platform's spelling
const slash = (path: string) => path.replace(/\\/g, '/')

function skillFile(dir: string) {
  const name = dir.split('/').pop()
  return `---\nname: "${name}"\ndescription: "Описание ${name}"\n${SKILLS[dir]}\n---\n\nТекст скилла`
}

type Kit = {
  isConnected?: boolean
  agents?: unknown[]
  ran?: { command: string; args: string }[]
  filled?: string[]
  memoryLines?: number
  statuses?: (string | undefined)[]
  engine?: string
  settings?: string
  written?: { path: string; text: string }[]
  isPlaced?: boolean
  opened?: boolean[]
  stored?: Record<string, unknown>
  profiles?: string
  toasts?: string[]
  kitVersion?: string
  root?: string
  logs?: { text: string; to?: string }[]
  // What the band holds beneath the deck: the engine's own node by default, another mod's tree when given
  bandKey?: string
}

// The node core hands next(e) for a site it draws itself
const ENGINE_TREE = { type: 'engine', ref: 0 }

function stubKit(on, kit: Kit) {
  mock.clock(on, { now: 60_000 })
  mock.store(on, kit.stored ?? {})
  on('session.start', () => ({ cwd: kit.root ?? PROJECT }))
  on('session.root', () => ({ value: kit.root ?? PROJECT }))
  on('command.register', () => ({ value: undefined }))
  on('command.list', () => ({ value: COMMANDS }))
  on('session.version', () => ({ value: { version: kit.engine ?? '2.1.296', base: kit.engine ?? '2.1.296' } }))
  on('agent.list', () => ({ value: kit.agents ?? [] }))
  on('ui.open', ($, e) => {
    kit.opened?.push(Boolean(e.focus))
    // The person's open (focus) is placed at any width
    return { value: kit.isPlaced === false && !e.focus ? { isPlaced: false, reason: UNASKED_REASON } : { isPlaced: true } }
  })
  on('ui.render', { component: 'AbovePrompt' }, ($, e) =>
    kit.bandKey ? $.ui.resolve(e).Box({ key: kit.bandKey, children: [] }) : ENGINE_TREE,
  )
  on('ui.log', ($, e) => {
    kit.logs?.push({ text: e.text, to: e.to })
    return { value: undefined }
  })
  on('ui.toast', ($, e) => {
    kit.toasts?.push(e.text)
    return { value: undefined }
  })
  on('ui.status', ($, e) => {
    kit.statuses?.push(e.text)
    return { value: undefined }
  })
  on('fs.exists', ($, e) => ({ value: slash(e.path).endsWith('base/skills') }))
  on('fs.list', ($, e) => {
    const dirs = Object.keys(SKILLS).filter(dir => slash(e.path).endsWith(dir.slice(0, dir.lastIndexOf('/'))))
    return { value: dirs.map(dir => ({ name: dir.split('/').pop(), kind: 'dir', size: 0, isLink: false })) }
  })
  on('fs.read', ($, e) => {
    if (slash(e.path).endsWith('.aikit/profiles.json')) return kit.isConnected === false ? { deny: 'missing' } : { value: kit.profiles ?? PROFILES }
    if (slash(e.path).endsWith('.aikit/plugin-init.json')) return { deny: 'missing' }
    if (slash(e.path).endsWith('.claude-plugin/plugin.json')) return kit.kitVersion ? { value: JSON.stringify({ name: 'aikit', version: kit.kitVersion }) } : { deny: 'missing' }
    if (slash(e.path).endsWith('.aikit/settings.json')) return kit.settings === undefined ? { deny: 'missing' } : { value: kit.settings }
    if (slash(e.path).endsWith('.aikit/memory/INDEX.md')) {
      if (kit.memoryLines === undefined) return { deny: 'missing' }
      return { value: Array.from({ length: kit.memoryLines }, (_, i) => `- запись ${i}\n`).join('') }
    }
    const dir = Object.keys(SKILLS).find(item => slash(e.path).endsWith(item + '/SKILL.md'))
    return dir ? { value: skillFile(dir) } : { deny: 'missing' }
  })
  on('fs.write', ($, e) => {
    kit.written?.push({ path: slash(e.path), text: e.text })
    return { value: undefined }
  })
  on('command.run', ($, e) => {
    kit.ran?.push({ command: e.command, args: e.args })
    return {}
  })
  on('prompt.fill', ($, e) => {
    kit.filled?.push(e.text)
    return { isFilled: true }
  })
}

async function start($) {
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: PROJECT })
}

test('argument hints become toggles and a field', () => {
  expect(parseArgumentHint('[--tdd] [--worktree] <задача>')).toEqual({
    flags: ['--tdd', '--worktree'],
    field: { placeholder: 'задача', isRequired: true },
  })
  expect(parseArgumentHint('[--no-test] [--no-review] <описание бага>')).toEqual({
    flags: ['--no-test', '--no-review'],
    field: { placeholder: 'описание бага', isRequired: true },
  })
  expect(parseArgumentHint('[путь]')).toEqual({ flags: [], field: { placeholder: 'путь', isRequired: false } })
  expect(parseArgumentHint('<файл и ссылка на макет>').field?.placeholder).toBe('файл и ссылка на макет')
  expect(parseArgumentHint(undefined)).toEqual({ flags: [], field: null })
})

test('frontmatter values lose their quotes', () => {
  expect(parseFrontmatter('---\nname: "fix-bug"\nargument-hint: \'<баг>\'\n---\nbody')).toEqual({ name: 'fix-bug', 'argument-hint': '<баг>' })
  expect(parseFrontmatter('no frontmatter')).toEqual({})
})

test('a namespaced plugin command is found by its skill name', () => {
  const entry = { skill: 'setup', owner: 'aikit' }
  expect(resolveCommandName(entry, [{ name: 'aikit:setup' }])).toBe('aikit:setup')
  expect(resolveCommandName(entry, [{ name: 'setup' }])).toBe('setup')
  expect(resolveCommandName(entry, [])).toBe(null)
})

test('running subagents come first and finished ones keep their time', () => {
  const timing = new Map()
  trackTiming(timing, [{ id: 'a', status: 'running' }, { id: 'b', status: 'running' }], 0)
  trackTiming(timing, [{ id: 'a', status: 'running' }, { id: 'b', status: 'completed' }], 65_000)
  const rows = agentRows([{ id: 'b', status: 'completed' }, { id: 'a', status: 'running' }], timing, 125_000, 3)
  expect(rows.map(row => [row.id, row.elapsed])).toEqual([
    ['a', '2:05'],
    ['b', '1:05'],
  ])
})

test('the pane shows base and profile commands, hides convention and Codex-only skills', async ($, on) => {
  stubKit(on, {})
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'cmd-aikit-implement-feature' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-aikit-setup' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-vue-nuxt-new-page' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-aikit-git-commit' })).toBeUndefined()
  expect(await ui.find({ key: 'cmd-aikit-update-agents' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: 'Профиль vue-nuxt · web/' })).toBeDefined()
})

test('a command with a field runs with flags and text, in send mode by default', async ($, on) => {
  const kit: Kit = { ran: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'cmd-aikit-implement-feature' })
  await ui.input({ key: 'arg', text: '' })
  expect(await ui.find({ type: 'Text', text: 'Заполните: задача' })).toBeDefined()
  expect(kit.ran).toEqual([])
  await ui.press({ key: 'flag---tdd' })
  await ui.input({ key: 'arg', text: 'фильтр заказов' })
  expect(kit.ran).toEqual([{ command: 'implement-feature', args: '--tdd фильтр заказов' }])
  expect(await ui.find({ type: 'Button', text: /\/implement-feature --tdd фильтр заказов$/ })).toBeDefined()
})

test('a command without arguments runs at once; fill mode puts it in the prompt', async ($, on) => {
  const kit: Kit = { ran: [], filled: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'cmd-aikit-memory-status' })
  expect(kit.ran).toEqual([{ command: 'memory-status', args: '' }])
  await ui.press({ key: 'mode' })
  await ui.press({ key: 'cmd-vue-nuxt-new-page' })
  await ui.input({ key: 'arg', text: 'orders/[id]' })
  expect(kit.filled).toEqual(['/new-page orders/[id] '])
})

test('subagents started from the chat show with their status', async ($, on) => {
  stubKit(on, {
    agents: [
      { id: 'a1', type: 'vue-coder', description: 'Фильтр заказов', status: 'running' },
      { id: 'a2', type: 'vue-architect', description: 'План фичи', status: 'completed' },
    ],
  })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'работают: 1' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'vue-coder' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^готово · / })).toBeDefined()
})

test('the reference tab lists commands with hints and filters them', async ($, on) => {
  stubKit(on, {})
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'tab-docs' })
  expect(await ui.find({ type: 'Text', text: '/implement-feature [--tdd] [--worktree] <задача>' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'Пример: /implement-feature страница заказов' })).toBeDefined()
  await ui.input({ key: 'docs-filter', text: 'new-page', kind: 'change' })
  expect(await ui.find({ type: 'Text', text: '/new-page <маршрут>' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^\/memory-status/ })).toBeUndefined()
})

test('a project without AIKit shows base commands and offers setup', async ($, on) => {
  stubKit(on, { isConnected: false })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'setup' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-aikit-implement-feature' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-vue-nuxt-new-page' })).toBeUndefined()
})

test('memory size uses the /memory-status limits', () => {
  expect(memorySummary(null)).toEqual({ lines: null, needsOptimize: false })
  expect(memorySummary('a\nb\n')).toEqual({ lines: 2, needsOptimize: false })
  expect(memorySummary(Array(51).fill('x').join('\n')).needsOptimize).toBe(true)
})

test('a full INDEX shows in the header and as a line under the prompt', async ($, on) => {
  const kit: Kit = { memoryLines: 55, statuses: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'память 55/60 — пора /optimize-memory' })).toBeDefined()
  expect(kit.statuses).toEqual(['память: INDEX 55/60 строк — пора /optimize-memory'])
})

test('a small INDEX shows its size and no line under the prompt', async ($, on) => {
  const kit: Kit = { memoryLines: 12, statuses: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'память 12/60' })).toBeDefined()
  expect(kit.statuses).toEqual([undefined])
})

test('cards show the first clause of a description', () => {
  expect(summary('Реализовать фичу через цепочку агентов: архитектор → кодер. Флаги')).toBe('Реализовать фичу через цепочку агентов')
  expect(summary('Показать состояние памяти')).toBe('Показать состояние памяти')
})

test('typography is used from the engine release that draws it', () => {
  expect(isAtLeast('2.1.299', '2.1.299')).toBe(true)
  expect(isAtLeast('2.1.300', '2.1.299')).toBe(true)
  expect(isAtLeast('2.2.0', '2.1.299')).toBe(true)
  expect(isAtLeast('2.1.296', '2.1.299')).toBe(false)
  expect(isAtLeast(undefined, '2.1.299')).toBe(false)
})

test('from 2.1.299 the pane draws headings, primary buttons and checkboxes', async ($, on) => {
  stubKit(on, { engine: '2.1.299' })
  await start($)
  let ui
  try {
    ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  } catch (error) {
    // The engine running the test validates the tree; one before 2.1.299 refuses typography props
    if (/prop "(size|weight)" is not allowed/.test(String(error))) return
    throw error
  }
  await ui.press({ key: 'cmd-aikit-implement-feature' })
  expect(await ui.find({ type: 'Button', text: '☐ --tdd' })).toBeDefined()
  await ui.press({ key: 'flag---tdd' })
  expect(await ui.find({ type: 'Button', text: '☑ --tdd' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'Разработка' })).toBeDefined()
})

test('the commit toggle writes the team setting and keeps other keys', async ($, on) => {
  const kit: Kit = { settings: JSON.stringify({ commit: 'ask', other: 1 }), written: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Button', text: '☐ Коммит без вопроса' })).toBeDefined()
  await ui.press({ key: 'commit' })
  expect(kit.written?.length).toBe(1)
  expect(kit.written?.[0].path.endsWith(PROJECT + '/.aikit/settings.json')).toBe(true)
  expect(JSON.parse(kit.written?.[0].text ?? '')).toEqual({ commit: 'auto', other: 1 })
  expect(await ui.find({ type: 'Button', text: '☑ Коммит без вопроса' })).toBeDefined()
})

test('a repository with team settings alone, like the kit itself, has the commit toggle', async ($, on) => {
  const kit: Kit = { isConnected: false, settings: JSON.stringify({ commit: 'auto' }), written: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Button', text: '☑ Коммит без вопроса' })).toBeDefined()
  await ui.press({ key: 'commit' })
  expect(JSON.parse(kit.written?.[0].text ?? '')).toEqual({ commit: 'ask' })
})

test('a project without AIKit has no commit toggle', async ($, on) => {
  stubKit(on, { isConnected: false })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'commit' })).toBeUndefined()
})

test('while the deck is closed a button in the prompt footer opens it, beside the mode labels', async ($, on) => {
  const kit: Kit = { isPlaced: false, opened: [] }
  stubKit(on, kit)
  await start($)
  const footer = await $.ui.mount({ ...FOOTER, surface: 'desktop' })
  expect(await footer.find({ type: 'Text', text: 'focus' })).toBeDefined()
  await footer.press({ key: 'open-deck' })
  expect(kit.opened).toEqual([false, true])
})

test('the button hides while the deck is open and in a project that never used it', async ($, on) => {
  stubKit(on, {})
  // The engine's own footer
  on('ui.render', ($, e) => $.ui.resolve(e).Box({ key: 'engine-footer', children: [] }))
  await start($)
  const footer = await $.ui.mount({ ...FOOTER, surface: 'terminal' })
  expect(await footer.find({ key: 'open-deck' })).toBeUndefined()
  expect(await footer.find({ key: 'engine-footer' })).toBeDefined()
})

test('the project own skills show; improve-aikit joins the kit group, a copy of a kit skill is skipped', async ($, on) => {
  const kit: Kit = { isConnected: false, settings: JSON.stringify({ commit: 'auto' }), ran: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'cmd-project-run-evals' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'Скиллы проекта' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-project-implement-feature' })).toBeUndefined()
  await ui.press({ key: 'cmd-project-improve-aikit' })
  await ui.input({ key: 'arg', text: 'кнопка в деке' })
  expect(kit.ran).toEqual([{ command: 'improve-aikit', args: 'кнопка в деке' }])
})

test('the deck opens at session start in the kit repository', async ($, on) => {
  const kit: Kit = { isConnected: false, settings: JSON.stringify({ commit: 'auto' }), opened: [] }
  stubKit(on, kit)
  await start($)
  expect(kit.opened).toEqual([false])
})

test('a folder where the deck was opened before gets it at session start', async ($, on) => {
  const kit: Kit = { isConnected: false, stored: { ['opened:' + PROJECT]: true }, opened: [] }
  stubKit(on, kit)
  await start($)
  expect(kit.opened).toEqual([false])
})

test('a deck left unplaced at session start logs why and offers a button in the band above the prompt; the press opens it', async ($, on) => {
  const kit: Kit = { isPlaced: false, opened: [], logs: [] }
  stubKit(on, kit)
  await start($)
  expect(kit.logs).toEqual([{ text: `AIKit Deck: панель ждёт размещения — ${UNASKED_REASON}`, to: 'debug' }])
  const band = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await band.find({ type: 'Text', text: 'AIKit Deck' })).toBeDefined()
  await band.press({ key: 'band-open-deck' })
  expect(kit.opened).toEqual([false, true])
  expect(await band.find({ key: 'band-open-deck' })).toBeUndefined()
})

test('the band stays empty while the deck is open', async ($, on) => {
  stubKit(on, {})
  await start($)
  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await band.find({ key: 'band-open-deck' })).toBeUndefined()
})

test('a survey in the band keeps it', async ($, on) => {
  stubKit(on, { isPlaced: false })
  await start($)
  const band = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true }, surface: 'terminal' })
  expect(await band.find({ key: 'band-open-deck' })).toBeUndefined()
})

test('another mod holding the band keeps it', async ($, on) => {
  stubKit(on, { isPlaced: false, bandKey: 'other-band' })
  await start($)
  const band = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await band.find({ key: 'other-band' })).toBeDefined()
  expect(await band.find({ key: 'band-open-deck' })).toBeUndefined()
})

test('a project without AIKit that never used the deck has no band button', async ($, on) => {
  stubKit(on, { isConnected: false, isPlaced: false })
  await start($)
  const band = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await band.find({ key: 'band-open-deck' })).toBeUndefined()
})

test('a project without AIKit that never used the deck does not get it at session start', async ($, on) => {
  const kit: Kit = { isConnected: false, opened: [] }
  stubKit(on, kit)
  await start($)
  expect(kit.opened).toEqual([])
})

test('model names lose the claude- prefix and the date', () => {
  expect(shortModel('claude-haiku-4-5-20251001')).toBe('haiku-4-5')
  expect(shortModel('claude-opus-4-7')).toBe('opus-4-7')
  expect(shortModel(undefined)).toBe('')
})

test('a subagent row shows the model from the agent list', async ($, on) => {
  stubKit(on, { agents: [{ id: 'a1', type: 'vue-coder', description: 'Фильтр заказов', status: 'running', model: 'claude-sonnet-4-6' }] })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'sonnet-4-6' })).toBeDefined()
})

test('a subagent row shows the model its requests went to', async ($, on) => {
  stubKit(on, { agents: [{ id: 'a1', type: 'vue-coder', description: 'Фильтр заказов', status: 'running' }] })
  on('turn.step', async function* ($, e) {
    yield { kind: 'text', index: 0, text: 'ok' }
    return { turnId: e.turnId, index: e.index, answer: 'ok', toolUses: [], stopReason: 'end_turn', usage: { input_tokens: 1, output_tokens: 1, model: 'claude-haiku-4-5-20251001' } }
  })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'haiku-4-5' })).toBeUndefined()
  const stream = $.turn.step({ turnId: 't', index: 0, model: 'claude-haiku-4-5', messageCount: 1, agentId: 'a1' })
  let step = await stream.next()
  while (step.done !== true) step = await stream.next()
  expect(step.value.answer).toBe('ok')
  expect(await ui.find({ type: 'Text', text: 'haiku-4-5' })).toBeDefined()
})

type Spawned = { argv: readonly string[]; cwd?: string }

// A stand-in for the host: each spawn prints its argv and exits with the code the test gives
function stubSpawn(on, spawned: Spawned[], code = 0) {
  on('process.spawn', async function* ($, e) {
    spawned.push({ argv: e.argv, cwd: e.cwd })
    yield { stream: 'stdout', text: `> ${e.argv.join(' ')}\nBUILD ` }
    yield { stream: 'stdout', text: 'SUCCESSFUL\n' }
    return { value: { code, signal: null } }
  })
}

const WAIT_ATTEMPTS = 50
const WAIT_STEP_MS = 10

// Actions run in the background of a press: wait until the pane shows what the test expects
async function waitFor(ui, query) {
  for (let attempt = 0; attempt < WAIT_ATTEMPTS; attempt += 1) {
    const found = await ui.find(query)
    if (found) return found
    await new Promise(resolve => setTimeout(resolve, WAIT_STEP_MS))
  }
  return undefined
}

test('profile actions come from the contract, the plugin update is added to every profile', () => {
  const actions = profileActions({ name: 'forge-1-12-java', root: 'mod' }, { ...JAVA_ACTIONS, broken: { label: 'Нет argv' }, empty: { argv: [] } })
  expect(actions.map(action => action.id)).toEqual(['compileJava', 'runClient', 'update-plugin'])
  expect(actions[0]).toEqual({ id: 'compileJava', label: 'Компиляция', description: 'Компиляция мода', steps: [['./gradlew', 'compileJava']], cwd: 'mod' })
  expect(actions[2].steps).toEqual([
    ['claude', 'plugin', 'marketplace', 'update', 'aikit'],
    ['claude', 'plugin', 'update', 'forge-1-12-java@aikit'],
  ])
  expect(profileActions({ name: 'vue-nuxt', root: 'web' }, undefined).map(action => action.id)).toEqual(['update-plugin'])
  expect(actionLine(actions[2].steps)).toBe('claude plugin marketplace update aikit && claude plugin update forge-1-12-java@aikit')
})

test('on Windows an action runs through cmd.exe: a program of the profile folder by an explicit .\\ path, others by PATH', () => {
  expect(hostArgv(['./gradlew', 'compileJava'], false)).toEqual({ argv: ['./gradlew', 'compileJava'] })
  // With NoDefaultCurrentDirectoryInExePath cmd.exe finds a bare gradlew.bat nowhere, .\gradlew.bat runs
  expect(hostArgv(['./gradlew', 'compileJava'], true)).toEqual({ argv: ['cmd', '/d', '/c', '.\\gradlew.bat', 'compileJava'] })
  expect(hostArgv(['.\\gradlew', 'build'], true)).toEqual({ argv: ['cmd', '/d', '/c', '.\\gradlew.bat', 'build'] })
  expect(hostArgv(['gradlew', 'test'], true)).toEqual({ argv: ['cmd', '/d', '/c', '.\\gradlew.bat', 'test'] })
  expect(hostArgv(['gradlew.bat', 'test'], true)).toEqual({ argv: ['cmd', '/d', '/c', '.\\gradlew.bat', 'test'] })
  expect(hostArgv(['./scripts/run.cmd', 'dev'], true)).toEqual({ argv: ['cmd', '/d', '/c', '.\\scripts\\run.cmd', 'dev'] })
  expect(hostArgv(['claude', 'plugin', 'update', 'aikit@aikit'], true)).toEqual({ argv: ['cmd', '/d', '/c', 'claude', 'plugin', 'update', 'aikit@aikit'] })
  expect(hostArgv(['git', 'status'], true)).toEqual({ argv: ['cmd', '/d', '/c', 'git', 'status'] })
  expect(hostArgv(['./gradlew', 'test & del x'], true).error).toBeDefined()
  expect(isWindowsPath('E:\\Minecraft\\mod')).toBe(true)
  expect(isWindowsPath('C:/work')).toBe(true)
  expect(isWindowsPath('/work/shop')).toBe(false)
})

test('the output keeps the last lines, a line split between pieces is joined', () => {
  let tail = appendOutput({ lines: [], partial: '' }, 'a\nb', 3)
  tail = appendOutput(tail, 'c\r\n\u001b[32md\u001b[0m\n\ne\nf', 3)
  expect(tail).toEqual({ lines: ['bc', 'd', 'e'], partial: 'f' })
  expect(outputLines(tail, 3)).toEqual(['d', 'e', 'f'])
})

test('a project action runs by argv without the model and shows its status and output', async ($, on) => {
  const spawned: Spawned[] = []
  stubKit(on, { profiles: JAVA_PROFILES })
  stubSpawn(on, spawned)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'Действия проекта' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: './gradlew compileJava' })).toBeDefined()
  await ui.press({ key: 'action-forge-1-12-java:compileJava' })
  expect(await waitFor(ui, { type: 'Text', text: '✓ завершено, код 0' })).toBeDefined()
  expect(spawned).toEqual([{ argv: ['./gradlew', 'compileJava'], cwd: PROJECT }])
  expect(await ui.find({ type: 'Text', text: 'BUILD SUCCESSFUL' })).toBeDefined()
})

test('on Windows a Gradle action starts as .\\gradlew.bat through cmd.exe in the profile folder', async ($, on) => {
  const spawned: Spawned[] = []
  stubKit(on, { profiles: JAVA_PROFILES, root: 'E:\\Minecraft\\mod' })
  stubSpawn(on, spawned)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'action-forge-1-12-java:compileJava' })
  expect(await waitFor(ui, { type: 'Text', text: '✓ завершено, код 0' })).toBeDefined()
  expect(spawned).toEqual([{ argv: ['cmd', '/d', '/c', '.\\gradlew.bat', 'compileJava'], cwd: 'E:/Minecraft/mod' }])
})

test('a failing action shows its exit code', async ($, on) => {
  stubKit(on, { profiles: JAVA_PROFILES })
  stubSpawn(on, [], 1)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'action-forge-1-12-java:compileJava' })
  expect(await waitFor(ui, { type: 'Text', text: '✗ завершено, код 1' })).toBeDefined()
})

test('a running action is not started twice and Stop ends it', async ($, on) => {
  const spawned: Spawned[] = []
  let release = () => {}
  const held = new Promise<void>(resolve => (release = resolve))
  stubKit(on, { profiles: JAVA_PROFILES })
  on('process.spawn', async function* ($, e) {
    spawned.push({ argv: e.argv, cwd: e.cwd })
    yield { stream: 'stdout', text: 'Minecraft started\n' }
    await held
    return { value: { code: 0, signal: null } }
  })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'action-forge-1-12-java:runClient' })
  expect(await waitFor(ui, { key: 'stop-forge-1-12-java:runClient' })).toBeDefined()
  await ui.press({ key: 'action-forge-1-12-java:runClient' })
  expect(spawned.length).toBe(1)
  await ui.press({ key: 'stop-forge-1-12-java:runClient' })
  release()
  expect(await waitFor(ui, { type: 'Text', text: '✗ остановлено' })).toBeDefined()
  expect(await ui.find({ key: 'stop-forge-1-12-java:runClient' })).toBeUndefined()
})

// Toasts come from work a press leaves running: wait until one arrives
async function waitForToast(toasts: string[]) {
  for (let attempt = 0; attempt < WAIT_ATTEMPTS && toasts.length === 0; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, WAIT_STEP_MS))
  }
  return toasts
}

test('a profile without its own actions has the plugin update alone; its result is a toast, not the output block', async ($, on) => {
  const spawned: Spawned[] = []
  const kit: Kit = { toasts: [] }
  stubKit(on, kit)
  stubSpawn(on, spawned)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'action-vue-nuxt:update-plugin' })).toBeDefined()
  expect(await ui.find({ key: 'action-vue-nuxt:compileJava' })).toBeUndefined()
  await ui.press({ key: 'action-vue-nuxt:update-plugin' })
  expect(await waitForToast(kit.toasts ?? [])).toEqual(['Профиль vue-nuxt обновлён — изменения подхватятся после перезапуска сессии'])
  expect(spawned.map(item => item.argv.join(' '))).toEqual(['claude plugin marketplace update aikit', 'claude plugin update vue-nuxt@aikit'])
  expect(await ui.find({ key: 'action-output' })).toBeUndefined()
  expect(await ui.find({ key: 'action-status-vue-nuxt:update-plugin' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: 'BUILD SUCCESSFUL' })).toBeUndefined()
})

test('a running plugin update shows that it works, without Stop', async ($, on) => {
  let release = () => {}
  const held = new Promise<void>(resolve => (release = resolve))
  const kit: Kit = { toasts: [] }
  stubKit(on, kit)
  on('process.spawn', async function* () {
    yield { stream: 'stdout', text: 'Updating marketplace\n' }
    await held
    return { value: { code: 0, signal: null } }
  })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  void ui.press({ key: 'action-vue-nuxt:update-plugin' })
  expect(await waitFor(ui, { type: 'Text', text: '● работает' })).toBeDefined()
  expect(await ui.find({ key: 'stop-vue-nuxt:update-plugin' })).toBeUndefined()
  release()
  expect((await waitForToast(kit.toasts ?? [])).length).toBe(1)
})

test('the header button on its own row updates the marketplace and the core plugin, the toast asks for a restart', async ($, on) => {
  const spawned: Spawned[] = []
  const kit: Kit = { isConnected: false, settings: JSON.stringify({ commit: 'auto' }), toasts: [] }
  stubKit(on, kit)
  stubSpawn(on, spawned)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'update-kit' })
  expect(await waitForToast(kit.toasts ?? [])).toEqual(['Кит обновлён — изменения подхватятся после перезапуска сессии'])
  expect(spawned.map(item => item.argv.join(' '))).toEqual(['claude plugin marketplace update aikit', 'claude plugin update aikit@aikit'])
  expect(await ui.find({ type: 'Text', text: /перезапуска сессии/ })).toBeUndefined()
  expect(await ui.find({ key: 'action-output' })).toBeUndefined()
})

test('a failed kit update is a toast with the code and the last line of output', async ($, on) => {
  const kit: Kit = { toasts: [] }
  stubKit(on, kit)
  stubSpawn(on, [], 1)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'update-kit' })
  expect(await waitForToast(kit.toasts ?? [])).toEqual(['Кит не обновлён: завершено, код 1 — BUILD SUCCESSFUL'])
  expect(await ui.find({ type: 'Text', text: /завершено, код 1/ })).toBeUndefined()
})

test('a kit update whose plugin step fails after the marketplace one is not reported as updated', async ($, on) => {
  const spawned: Spawned[] = []
  const kit: Kit = { toasts: [], kitVersion: '0.7.0' }
  stubKit(on, kit)
  on('process.spawn', async function* ($, e) {
    spawned.push({ argv: e.argv, cwd: e.cwd })
    const isMarketplace = e.argv.includes('marketplace')
    yield { stream: 'stderr', text: isMarketplace ? 'Marketplace updated\n' : 'error: plugin not found\n' }
    return { value: { code: isMarketplace ? 0 : 1, signal: null } }
  })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'update-kit' })
  expect(await waitForToast(kit.toasts ?? [])).toEqual(['Кит не обновлён: завершено, код 1 — error: plugin not found'])
  expect(spawned.length).toBe(2)
})

test('the header shows the version of the kit the session runs; without a manifest just its name', async ($, on) => {
  stubKit(on, { kitVersion: '0.7.0' })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'кит aikit 0.7.0' })).toBeDefined()
  // Loaded with --plugin-dir, as here, the core plugin has no install record: profiles show without a version
  expect(await ui.find({ type: 'Text', text: 'vue-nuxt (web/)' })).toBeDefined()
})

test('without a kit manifest the header names the kit alone', async ($, on) => {
  stubKit(on, {})
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'кит aikit' })).toBeDefined()
})

const INSTALLED = {
  version: 2,
  plugins: {
    'aikit@aikit': [
      { scope: 'user', installPath: 'C:\\Users\\dev\\.claude\\plugins\\cache\\aikit\\aikit\\0.7.0', version: '0.7.0' },
      { scope: 'project', projectPath: 'E:\\Minecraft\\mod', version: '0.6.0' },
    ],
    'forge-1-12-java@aikit': [
      { scope: 'project', projectPath: 'E:\\Minecraft\\other', version: '0.5.0' },
      { scope: 'project', projectPath: 'E:\\Minecraft\\mod', version: '0.7.0' },
    ],
    'vue-nuxt@aikit': [{ scope: 'local', projectPath: '/work/shop', version: '0.6.0' }, { scope: 'user', version: '0.7.0' }],
  },
}

test('the install record of this project wins over the user one; another project and no record give nothing', () => {
  expect(installedVersion(INSTALLED, 'forge-1-12-java', ['E:/Minecraft/mod'])).toBe('0.7.0')
  expect(installedVersion(INSTALLED, 'forge-1-12-java', ['e:/minecraft/MOD/'])).toBe('0.7.0')
  expect(installedVersion(INSTALLED, 'forge-1-12-java', ['E:/Minecraft/third'])).toBe(null)
  expect(installedVersion(INSTALLED, 'aikit', ['E:/Minecraft/mod'])).toBe('0.6.0')
  expect(installedVersion(INSTALLED, 'aikit', ['E:/Minecraft/third'])).toBe('0.7.0')
  expect(installedVersion(INSTALLED, 'vue-nuxt', [null, '/work/shop'])).toBe('0.6.0')
  expect(installedVersion(INSTALLED, 'vue-nuxt', ['/work/Shop'])).toBe('0.7.0')
  expect(installedVersion(INSTALLED, 'tma', ['/work/shop'])).toBe(null)
  expect(installedVersion(null, 'aikit', ['/work/shop'])).toBe(null)
})

test('the install records sit beside the plugin cache; a plugin outside the cache has none', () => {
  expect(pluginsDir('C:\\Users\\dev\\.claude\\plugins\\cache\\aikit\\aikit\\0.7.0')).toBe('C:/Users/dev/.claude/plugins')
  expect(pluginsDir('/home/dev/.config/claude/plugins/cache/aikit/aikit/0.7.0')).toBe('/home/dev/.config/claude/plugins')
  expect(pluginsDir('D:\\dev\\ai-kit')).toBe(null)
})

test('the update toast tells the versions, an update with nothing new and an error', () => {
  const done = { status: 'done', code: 0, tail: { lines: [], partial: '' } }
  const failed = { status: 'failed', code: 1, tail: { lines: ['error: plugin not found'], partial: '' } }
  expect(updateToast('Профиль forge-1-12-java', done, '0.6.0', '0.7.0')).toBe('Профиль forge-1-12-java обновлён: 0.6.0 → 0.7.0 — изменения подхватятся после перезапуска сессии')
  expect(updateToast('Кит', done, '0.7.0', '0.7.0')).toBe('Кит: уже последняя версия 0.7.0')
  expect(updateToast('Кит', done, null, '0.7.0')).toBe('Кит обновлён до 0.7.0 — изменения подхватятся после перезапуска сессии')
  expect(updateToast('Кит', failed, '0.6.0', null)).toBe('Кит не обновлён: завершено, код 1 — error: plugin not found')
})

// As in a live installed_plugins.json: the kit in the user scope and in the project scope of this project,
// the profile in this project and in another one, a managed record of the administrator
const LIVE_PROJECT = 'E:\\Minecraft\\eoc-mappet-utils'
const LIVE_INSTALLED = {
  version: 2,
  plugins: {
    'aikit@aikit': [
      { scope: 'project', projectPath: LIVE_PROJECT, version: '0.8.0' },
      { scope: 'managed', version: '0.5.0' },
      { scope: 'user', installPath: 'C:\\Users\\dev\\.claude\\plugins\\cache\\aikit\\aikit\\0.7.0', version: '0.7.0' },
      { scope: 'local', projectPath: 'E:\\Minecraft\\other', version: '0.6.0' },
    ],
    'forge-1-12-java@aikit': [
      { scope: 'project', projectPath: 'E:\\Minecraft\\other', version: '0.6.0' },
      { scope: 'project', projectPath: LIVE_PROJECT, version: '0.8.0' },
    ],
  },
}

test('an update refreshes the user record and this project records; managed and other projects stay', () => {
  const paths = ['E:/Minecraft/eoc-mappet-utils', 'E:/Minecraft/eoc-mappet-utils']
  expect(updateRecords(LIVE_INSTALLED, 'aikit', paths).map(record => [record.scope, record.version])).toEqual([
    ['user', '0.7.0'],
    ['project', '0.8.0'],
  ])
  expect(updateRecords(LIVE_INSTALLED, 'forge-1-12-java', paths).map(record => record.scope)).toEqual(['project'])
  expect(updateRecords(LIVE_INSTALLED, 'forge-1-12-java', ['e:/minecraft/EOC-MAPPET-UTILS/']).map(record => record.version)).toEqual(['0.8.0'])
  expect(updateRecords(LIVE_INSTALLED, 'aikit', ['E:/Minecraft/third']).map(record => record.scope)).toEqual(['user'])
  expect(updateRecords(LIVE_INSTALLED, 'vue-nuxt', paths)).toEqual([])
  expect(updateRecords(null, 'aikit', paths)).toEqual([])
  expect(newestVersion(updateRecords(LIVE_INSTALLED, 'aikit', paths))).toBe('0.8.0')
  expect(newestVersion([{ version: '0.10.0' }, { version: '0.9.1' }])).toBe('0.10.0')
  expect(newestVersion([])).toBe(null)
})

test('the update steps run the marketplace, then the plugin in every scope; no records — one step without --scope', () => {
  expect(pluginUpdateSteps('aikit', ['user', 'project'])).toEqual([
    ['claude', 'plugin', 'marketplace', 'update', 'aikit'],
    ['claude', 'plugin', 'update', 'aikit@aikit', '--scope', 'user'],
    ['claude', 'plugin', 'update', 'aikit@aikit', '--scope', 'project'],
  ])
  expect(pluginUpdateSteps('forge-1-12-java', ['project', 'project'])).toEqual([
    ['claude', 'plugin', 'marketplace', 'update', 'aikit'],
    ['claude', 'plugin', 'update', 'forge-1-12-java@aikit', '--scope', 'project'],
  ])
  expect(pluginUpdateSteps('aikit')).toEqual([
    ['claude', 'plugin', 'marketplace', 'update', 'aikit'],
    ['claude', 'plugin', 'update', 'aikit@aikit'],
  ])
})

test('a scope that failed after others is named in the toast, and the update is not reported as done', () => {
  const partial = {
    status: 'failed',
    code: 1,
    failedStep: ['claude', 'plugin', 'update', 'aikit@aikit', '--scope', 'project'],
    tail: { lines: ['✔ Plugin "aikit@aikit" updated', 'error: permission denied'], partial: '' },
  }
  expect(updateToast('Кит', partial, '0.7.0', null)).toBe('Кит не обновлён (scope project): завершено, код 1 — error: permission denied')
})

test('a project without AIKit has no project actions', async ($, on) => {
  stubKit(on, { isConnected: false })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'Действия проекта' })).toBeUndefined()
  expect(await ui.find({ key: 'update-kit' })).toBeDefined()
})
