const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const root = require('node:path').resolve(__dirname, '..')
const ts = require(`${root}/node_modules/typescript`)
const vue = require(`${root}/node_modules/vue`)
const sfc = require(`${root}/node_modules/@vue/compiler-sfc`)
const read = (name) => fs.readFileSync(`${root}/src/views/user/${name}View.vue`, 'utf8')
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); await vue.nextTick() }
function deferred() {
  let resolve, reject
  const promise = new Promise((a, b) => { resolve = a; reject = b })
  return { promise, resolve, reject }
}
function mount(name) {
  const text = read(name), { descriptor } = sfc.parse(text)
  const ast = ts.createSourceFile('view.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const statements = ast.statements.filter(n => !ts.isImportDeclaration(n))
  const names = statements.flatMap(n => ts.isVariableStatement(n) ? n.declarationList.declarations.map(d => d.name.text) : ts.isFunctionDeclaration(n) ? [n.name.text] : [])
  const code = statements.map(n => n.getFullText(ast)).join('\n')
  const js = ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const requests = [], mounted = [], unmounted = [], timers = new Map()
  let now = 0, timerId = 0
  const request = params => { const d = deferred(); requests.push({ params, ...d }); return d.promise }
  const mocks = {
    ref: vue.ref, computed: vue.computed, watch: vue.watch,
    onMounted: fn => mounted.push(fn), onBeforeUnmount: fn => unmounted.push(fn), onUnmounted: fn => unmounted.push(fn),
    useRouter: () => ({ push() {} }),
    useAuthStore: () => ({ user: { id: 1, platform_accounts: [{ id: 1, platform: 'codeforces', handle: 'mock' }] } }),
    listMyParticipations: request, listContests: request,
    listRankings: async () => ({ results: [] }), getMyBestRecord: async () => null, getRatingHistory: async () => [],
    SCORING_PLATFORMS: [{ key: 'codeforces', label: 'Codeforces' }, { key: 'atcoder', label: 'AtCoder' }],
    platformClass: x => x, platformLabel: x => x, initial: x => x.slice(0, 1),
    setTimeout: (fn, ms) => { const id = ++timerId; timers.set(id, { fn, at: now + ms }); return id },
    clearTimeout: id => timers.delete(id),
  }
  const scope = vue.effectScope()
  const state = scope.run(() => new Function(...Object.keys(mocks), `${js}\nreturn {${names.join(',')}}`)(...Object.values(mocks)))
  const m = { ...state, requests, timers, source: text,
    start() { for (const fn of mounted) fn() },
    stop() { for (const fn of unmounted) fn(); scope.stop() },
    advance(ms) { now += ms; for (const [id, timer] of [...timers]) if (timer.at <= now) { timers.delete(id); timer.fn() } },
  }
  return m
}
const response = (results, page = 1, count = results.length, totalPages = 1) => ({ results, page, count, page_size: 100, total_pages: totalPages })
const scoreRows = (count, start = 1) => Array.from({ length: count }, (_, i) => ({ id: start + i, contest_name: `Record ${start + i}`, contest_platform: 'codeforces', contest_start_time: new Date().toISOString(), new_rating: start + i, rating_delta: null, is_excluded: i === 0 }))
async function settle(m, index, value) { m.requests[index].resolve(value); await tick() }

for (const name of ['MyScores', 'Contests']) {
  test(`${name}: late response cannot overwrite current rows`, async t => {
    const m = mount(name); t.after(() => m.stop()); m.load(); m.platform.value = 'codeforces'; await tick()
    await settle(m, 1, response([{ id: 'current' }]))
    await settle(m, 0, response([{ id: 'stale' }]))
    assert.equal(m.rows.value[0].id, 'current')
  })
  test(`${name}: stale failure/finally cannot alter loading or error`, async t => {
    const m = mount(name); t.after(() => m.stop()); m.load(); m.platform.value = 'atcoder'; await tick()
    m.requests[0].reject(new Error('stale')); await tick()
    assert.equal(m.loading.value, true); assert.equal(m.error?.value, '')
    await settle(m, 1, response([])); assert.equal(m.loading.value, false)
  })
  test(`${name}: error clears records, retry recovers`, async t => {
    const m = mount(name); t.after(() => m.stop()); m.load(); await settle(m, 0, response([{ id: 1 }], 1, 100))
    m.load(); m.requests[1].reject(new Error('current')); await tick()
    assert.deepEqual([...m.rows.value], []); assert.ok(m.error?.value); assert.equal(m.loading.value, false)
    if (name === 'Contests') assert.equal(m.total.value, 0)
    m.load(); assert.equal(m.error.value, ''); await settle(m, 2, response([{ id: 2 }]))
    assert.equal(m.rows.value[0].id, 2)
  })
  test(`${name}: unmount invalidates pending response`, async () => {
    const m = mount(name); m.load(); m.stop(); await settle(m, 0, response([{ id: 'unmounted' }]))
    assert.deepEqual([...m.rows.value], [])
  })
  test(`${name}: SFC script and template compile`, () => {
    const { descriptor } = sfc.parse(read(name))
    const script = sfc.compileScript(descriptor, { id: name })
    const template = sfc.compileTemplate({ source: descriptor.template.content, filename: `${name}View.vue`, id: name, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  })
}
test('MyScores: follows total_pages to collect 205 rows, renders slices of 20, chart retains all rows', async t => {
  const m = mount('MyScores'); t.after(() => m.stop()); m.platform.value = 'codeforces'; await tick()
  await settle(m, 0, response(scoreRows(100), 1, 205, 3))
  assert.equal(m.requests.length, 2, 'must fetch second page')
  await settle(m, 1, response(scoreRows(100, 101), 2, 205, 3))
  await settle(m, 2, response(scoreRows(5, 201), 3, 205, 3))
  assert.deepEqual(m.requests.map(r => r.params), [1, 2, 3].map(page => ({ platform: 'codeforces', page, page_size: 100 })))
  assert.equal(m.rows.value.length, 205); assert.equal(m.pagedRows.value.length, 20)
  m.tablePage.value = 11; assert.equal(m.pagedRows.value.length, 5); assert.equal(m.pagedRows.value[0].id, 201)
  assert.equal(m.chartPoints.value.length, 205); assert.equal(m.unexcludedCount.value, 202)
  assert.doesNotMatch(m.source, /计入积分场数|countedCount|\.perf\b/)
  assert.match(m.source, /未排除记录/); assert.match(m.source, /不等同于计分场数/)
})
test('MyScores: platform changes synchronously clear rows and reset table page', async t => {
  const m = mount('MyScores'); t.after(() => m.stop()); m.load(); await settle(m, 0, response(scoreRows(25)))
  if (m.tablePage) m.tablePage.value = 2
  m.platform.value = 'atcoder'
  assert.equal(m.rows.value.length, 0); assert.equal(m.tablePage?.value, 1)
})
test('MyScores: stale intermediate page never publishes or requests another page', async t => {
  const m = mount('MyScores'); t.after(() => m.stop()); m.load()
  await settle(m, 0, response(scoreRows(100), 1, 300, 3)); assert.equal(m.requests.length, 2)
  m.platform.value = 'atcoder'; await tick()
  await settle(m, 1, response(scoreRows(100, 101), 2, 300, 3))
  assert.equal(m.requests.length, 3); assert.equal(m.rows.value.length, 0); assert.equal(m.loading.value, true)
  await settle(m, 2, response([]))
})
test('MyScores: intermediate page error publishes no partial total', async t => {
  const m = mount('MyScores'); t.after(() => m.stop()); m.load()
  await settle(m, 0, response(scoreRows(100), 1, 101, 2)); assert.equal(m.requests.length, 2)
  m.requests[1].reject(new Error('page 2')); await tick()
  assert.equal(m.rows.value.length, 0); assert.ok(m.error.value); assert.equal(m.loading.value, false)
})
for (const field of ['platform', 'rated', 'keyword']) {
  test(`Contests: ${field} resets page synchronously and requests once`, async t => {
    const m = mount('Contests'); t.after(() => m.stop()); m.page.value = 3; await tick()
    const before = m.requests.length
    m[field].value = ({ platform: 'atcoder', rated: 'yes', keyword: 'abc' })[field]
    assert.equal(m.page.value, 1)
    await tick(); m.advance(300); await tick()
    assert.equal(m.requests.length, before + 1); assert.equal(m.requests.at(-1).params.page, 1)
  })
}
test('Contests: typing immediately invalidates old success and debounces 300ms', async t => {
  const m = mount('Contests'); t.after(() => m.stop()); m.load(); m.keyword.value = 'a'
  await settle(m, 0, response([{ id: 'old' }], 1, 10))
  assert.equal(m.rows.value.length, 0); assert.equal(m.loading.value, true)
  assert.equal(m.requests.length, 1); m.advance(299); assert.equal(m.requests.length, 1)
  m.keyword.value = 'ab'; await tick(); m.advance(299); assert.equal(m.requests.length, 1)
  m.advance(1); await tick(); assert.equal(m.requests.length, 2); assert.equal(m.requests[1].params.name, 'ab')
})
test('Contests: typing immediately invalidates old error', async t => {
  const m = mount('Contests'); t.after(() => m.stop()); m.load(); m.keyword.value = 'a'
  m.requests[0].reject(new Error('old')); await tick()
  assert.equal(m.error?.value, ''); assert.equal(m.loading.value, true); assert.equal(m.requests.length, 1)
})
test('Contests: rapid pagination keeps only newest page', async t => {
  const m = mount('Contests'); t.after(() => m.stop()); m.page.value = 2; await tick(); m.page.value = 3; await tick()
  await settle(m, 1, response([{ id: 3 }], 1, 30)); await settle(m, 0, response([{ id: 2 }], 1, 20))
  assert.equal(m.rows.value[0].id, 3); assert.equal(m.total.value, 30)
})
test('Contests: local sort neither requests nor resets page and labels disclose scope', async t => {
  const m = mount('Contests'); t.after(() => m.stop()); m.page.value = 2; await tick()
  await settle(m, 0, response([{ id: 1, difficulty_factor: 1 }, { id: 2, difficulty_factor: 3 }]))
  const before = m.requests.length; m.sort.value = 'difficulty'; await tick()
  assert.equal(m.requests.length, before); assert.equal(m.page.value, 2); assert.equal(m.sortedRows.value[0].id, 2)
  assert.ok(m.sortOptions.every(o => o.label.startsWith('本页')))
})
test('Contests: changing platform during debounce cancels duplicate search request', async t => {
  const m = mount('Contests'); t.after(() => m.stop()); m.keyword.value = 'abc'; await tick(); m.platform.value = 'atcoder'; await tick()
  assert.equal(m.requests.length, 1); m.advance(300); await tick(); assert.equal(m.requests.length, 1)
  assert.equal(m.requests[0].params.name, 'abc'); assert.equal(m.requests[0].params.platform, 'atcoder')
})
test('Contests: unmount clears search timer', async () => {
  const m = mount('Contests'); m.keyword.value = 'abc'; await tick(); m.stop(); m.advance(300); await tick()
  assert.equal(m.requests.length, 0); assert.equal(m.timers.size, 0)
})
