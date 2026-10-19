import { expect, mock, test } from 'claude-code/testing'

import { agentRows, memorySummary, parseArgumentHint, parseFrontmatter, resolveCommandName, trackTiming } from '../catalog.js'

const PROJECT = '/work/shop'
const PROFILES = JSON.stringify({ profiles: { 'vue-nuxt': { label: 'Vue Nuxt', root: 'web' } } })
const SKILLS: Record<string, string> = {
  'base/skills/implement-feature': 'argument-hint: "[--tdd] [--worktree] <задача>"\nexample_prompt: "/implement-feature страница заказов"',
  'base/skills/memory-status': 'example_prompt: "/memory-status"',
  'base/skills/git-commit': 'user-invocable: false',
  'base/plugin-skills/setup': 'argument-hint: "[профили или пресет]"',
  'profiles/vue-nuxt/skills/new-page': 'argument-hint: "<маршрут>"',
}
const COMMANDS = [
  { name: 'implement-feature', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'memory-status', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'aikit:setup', description: '', source: 'plugin', plugin: 'aikit' },
  { name: 'new-page', description: '', source: 'plugin', plugin: 'vue-nuxt' },
]
const PANE = {
  plugin: 'aikit',
  component: 'Pane',
  requestId: 'aikit-deck',
  viewport: { columns: 120, rows: 40 },
  props: { title: 'AIKit Deck', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

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
}

function stubKit(on, kit: Kit) {
  mock.clock(on, { now: 60_000 })
  mock.store(on, {})
  on('session.start', () => ({ cwd: PROJECT }))
  on('session.root', () => ({ value: PROJECT }))
  on('command.register', () => ({ value: undefined }))
  on('command.list', () => ({ value: COMMANDS }))
  on('agent.list', () => ({ value: kit.agents ?? [] }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', () => ({ value: undefined }))
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
    if (slash(e.path).endsWith('.aikit/profiles.json')) return kit.isConnected === false ? { deny: 'missing' } : { value: PROFILES }
    if (slash(e.path).endsWith('.aikit/plugin-init.json')) return { deny: 'missing' }
    if (slash(e.path).endsWith('.aikit/memory/INDEX.md')) {
      if (kit.memoryLines === undefined) return { deny: 'missing' }
      return { value: Array.from({ length: kit.memoryLines }, (_, i) => `- запись ${i}\n`).join('') }
    }
    const dir = Object.keys(SKILLS).find(item => slash(e.path).endsWith(item + '/SKILL.md'))
    return dir ? { value: skillFile(dir) } : { deny: 'missing' }
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

test('the pane shows base and profile commands, hides convention skills', async ($, on) => {
  stubKit(on, {})
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ key: 'cmd-aikit-implement-feature' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-aikit-setup' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-vue-nuxt-new-page' })).toBeDefined()
  expect(await ui.find({ key: 'cmd-aikit-git-commit' })).toBeUndefined()
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
  expect(await ui.find({ type: 'Text', text: 'Субагенты · работают: 1' })).toBeDefined()
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
  expect(await ui.find({ type: 'Text', text: '· память 55/60 — пора /optimize-memory' })).toBeDefined()
  expect(kit.statuses).toEqual(['память: INDEX 55/60 строк — пора /optimize-memory'])
})

test('a small INDEX shows its size and no line under the prompt', async ($, on) => {
  const kit: Kit = { memoryLines: 12, statuses: [] }
  stubKit(on, kit)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: '· память 12/60' })).toBeDefined()
  expect(kit.statuses).toEqual([undefined])
})
