const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const root = require('node:path').resolve(__dirname, '..')
const ts = require(`${root}/node_modules/typescript`)
const vue = require(`${root}/node_modules/vue`)
const sfc = require(`${root}/node_modules/@vue/compiler-sfc`)

const read = (name) => fs.readFileSync(`${root}/src/views/user/${name}View.vue`, 'utf8')
const USE_RESOURCE_SOURCE = fs.readFileSync(`${root}/src/composables/useResource.ts`, 'utf8')
const TS_OPTIONS = { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true } }
const transpile = (code) => ts.transpileModule(code, TS_OPTIONS).outputText
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); await vue.nextTick() }
function deferred() {
  let resolve, reject
  const promise = new Promise((a, b) => { resolve = a; reject = b })
  return { promise, resolve, reject }
}

/**
 * 视图不再手写 requestSeq/loading/error，改为消费 useResource。
 * 这里把**真实的** useResource.ts 在同一套可控 mock 全局（测试自己的 setTimeout /
 * clearTimeout / onBeforeUnmount）里求值后注入，绝不能用假实现顶替，否则测不到序号作废。
 */
function compileUseResource(env) {
  const module = { exports: {} }
  new Function('module', 'exports', 'require', 'setTimeout', 'clearTimeout', transpile(USE_RESOURCE_SOURCE))(
    module,
    module.exports,
    (name) => {
      assert.equal(name, 'vue', `useResource.ts should only import vue, got ${name}`)
      return { ...vue, onBeforeUnmount: env.onBeforeUnmount }
    },
    env.setTimeout,
    env.clearTimeout,
  )
  assert.equal(typeof module.exports.useResource, 'function', 'useResource.ts must still export useResource')
  return module.exports.useResource
}

function mount(name) {
  const text = read(name), { descriptor } = sfc.parse(text)
  const ast = ts.createSourceFile('view.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const statements = ast.statements.filter(n => !ts.isImportDeclaration(n))
  const names = statements.flatMap(n => ts.isVariableStatement(n) ? n.declarationList.declarations.map(d => d.name.text) : ts.isFunctionDeclaration(n) ? [n.name.text] : [])
  const js = transpile(statements.map(n => n.getFullText(ast)).join('\n'))
  const requests = [], mounted = [], unmounted = [], timers = new Map(), calls = { rank: 0, best: 0, history: 0 }
  let now = 0, timerId = 0
  const request = params => { const d = deferred(); requests.push({ params, ...d }); return d.promise }
  const fakeSetTimeout = (fn, ms) => { const id = ++timerId; timers.set(id, { fn, at: now + ms }); return id }
  const fakeClearTimeout = id => timers.delete(id)
  const captureUnmount = fn => unmounted.push(fn)
  const mocks = {
    ref: vue.ref, computed: vue.computed, watch: vue.watch,
    onMounted: fn => mounted.push(fn), onBeforeUnmount: captureUnmount, onUnmounted: captureUnmount,
    useResource: compileUseResource({ onBeforeUnmount: captureUnmount, setTimeout: fakeSetTimeout, clearTimeout: fakeClearTimeout }),
    useRouter: () => ({ push() {} }),
    useAuthStore: () => ({ user: { id: 1, platform_accounts: [{ id: 1, platform: 'codeforces', handle: 'mock' }] } }),
    listMyParticipations: request, listContests: request,
    listRankings: async () => { calls.rank += 1; return { results: [] } },
    getMyBestRecord: async () => { calls.best += 1; return null },
    getRatingHistory: async () => { calls.history += 1; return [] },
    SCORING_PLATFORMS: [{ key: 'codeforces', label: 'Codeforces' }, { key: 'atcoder', label: 'AtCoder' }],
    platformClass: x => x, platformLabel: x => x, initial: x => x.slice(0, 1),
    setTimeout: fakeSetTimeout, clearTimeout: fakeClearTimeout,
  }
  const scope = vue.effectScope()
  const state = scope.run(() => new Function(...Object.keys(mocks), `${js}\nreturn {${names.join(',')}}`)(...Object.values(mocks)))
  const resource = state.records ?? state.list
  assert.ok(resource && typeof resource.reload === 'function', `${name}: view must build its list with useResource (records/list)`)
  const m = { ...state, resource, requests, timers, calls, source: text,
    start() { for (const fn of mounted) fn() },
    stop() { for (const fn of unmounted) fn(); scope.stop() },
    advance(ms) { now += ms; for (const [id, timer] of [...timers]) if (timer.at <= now) { timers.delete(id); timer.fn() } },
  }
  return m
}

const response = (results, page = 1, count = results.length, totalPages = 1) => ({ results, page, count, page_size: 100, total_pages: totalPages })
const scoreRows = (count, start = 1) => Array.from({ length: count }, (_, i) => ({ id: start + i, contest_name: `Record ${start + i}`, contest_platform: 'codeforces', contest_start_time: new Date().toISOString(), new_rating: start + i, rating_delta: null, is_excluded: i === 0 }))
async function settle(m, index, value) {
  assert.ok(m.requests[index], `expected request #${index}, but only ${m.requests.length} request(s) were sent`)
  m.requests[index].resolve(value); await tick()
}

for (const name of ['MyScores', 'Contests']) {
  test(`${name}: late response cannot overwrite current rows`, async t => {
    const m = mount(name); t.after(() => m.stop())
    assert.equal(m.requests.length, 1, 'immediate must fetch once at setup, without waiting for onMounted')
    assert.equal(m.loading.value, true)
    m.platform.value = 'codeforces'
    assert.equal(m.requests.length, 2, 'input change must invalidate and refetch synchronously')
    assert.equal(m.requests[0].params.platform, undefined, 'setup request carries the empty platform')
    assert.equal(m.requests[1].params.platform, 'codeforces')
    await settle(m, 1, response([{ id: 'current' }]))
    assert.equal(m.rows.value[0].id, 'current')
    await settle(m, 0, response([{ id: 'stale' }]))
    assert.deepEqual(m.rows.value.map(r => r.id), ['current'], 'superseded response must not overwrite the newest rows')
    assert.equal(m.loading.value, false, 'superseded response must not touch loading')
  })
  test(`${name}: stale failure and its finally cannot alter loading or error`, async t => {
    const m = mount(name); t.after(() => m.stop())
    m.platform.value = 'atcoder'
    m.requests[0].reject(new Error('stale'))
    await tick()
    assert.equal(m.loading.value, true, "a stale rejection's finally must not end the live request's loading state")
    assert.equal(m.error.value, '', 'a stale rejection must not publish an error')
    await settle(m, 1, response([]))
    assert.equal(m.loading.value, false)
    assert.equal(m.error.value, '')
  })
  test(`${name}: failure clears data and yields a retryable error, retry recovers`, async t => {
    const m = mount(name); t.after(() => m.stop())
    await settle(m, 0, response([{ id: 1 }], 1, 100))
    assert.equal(m.rows.value.length, 1)
    m.resource.reload()
    assert.equal(m.loading.value, true, 'reload enters loading synchronously')
    m.requests[1].reject(new Error('boom')); await tick()
    assert.deepEqual([...m.rows.value], [], 'failure must drop the previous rows instead of freezing them')
    assert.match(m.error.value, /加载失败/, 'view must surface a readable retry message')
    assert.equal(m.loading.value, false)
    if (name === 'Contests') assert.equal(m.total.value, 0, 'failure must drop the total too')
    m.resource.reload()
    assert.equal(m.error.value, '', 'retry clears the error before the response arrives')
    await settle(m, 2, response([{ id: 2 }], 1, 7))
    assert.equal(m.rows.value[0].id, 2)
    assert.equal(m.loading.value, false)
    if (name === 'Contests') assert.equal(m.total.value, 7)
  })
  test(`${name}: unmount drops a late success`, async () => {
    const m = mount(name)
    m.stop()
    await settle(m, 0, response([{ id: 'late' }]))
    assert.deepEqual([...m.rows.value], [], 'unmounted resource must not publish rows')
  })
  test(`${name}: unmount drops a late failure`, async () => {
    const m = mount(name)
    m.stop()
    m.requests[0].reject(new Error('late')); await tick()
    assert.equal(m.error.value, '', 'unmounted resource must not publish an error')
    assert.deepEqual([...m.rows.value], [], 'unmounted resource must not write rows')
  })
  test(`${name}: SFC script and template compile`, () => {
    const { descriptor } = sfc.parse(read(name))
    const script = sfc.compileScript(descriptor, { id: name })
    const template = sfc.compileTemplate({ source: descriptor.template.content, filename: `${name}View.vue`, id: name, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  })
}

test('MyScores: setup fetches records, onMounted only loads rank/best/history', async t => {
  const m = mount('MyScores'); t.after(() => m.stop())
  assert.equal(m.requests.length, 1, 'useResource immediate must own the records request')
  assert.deepEqual(m.calls, { rank: 0, best: 0, history: 0 }, 'no auxiliary API call may happen before onMounted')
  m.start()
  assert.deepEqual(m.calls, { rank: 1, best: 1, history: 1 })
  assert.equal(m.requests.length, 1, 'onMounted must not re-trigger the records request')
  await settle(m, 0, response(scoreRows(3)))
  assert.equal(m.rows.value.length, 3)
})

test('MyScores: follows total_pages to collect 205 rows, renders slices of 20, chart retains all rows', async t => {
  const m = mount('MyScores'); t.after(() => m.stop())
  m.platform.value = 'codeforces'
  await settle(m, 1, response(scoreRows(100), 1, 205, 3))
  assert.equal(m.requests.length, 3, 'page 1 of 3 must immediately fetch page 2')
  assert.equal(m.rows.value.length, 0, 'partial pages stay unpublished until the whole collection is in')
  assert.equal(m.loading.value, true)
  await settle(m, 2, response(scoreRows(100, 101), 2, 205, 3))
  await settle(m, 3, response(scoreRows(5, 201), 3, 205, 3))
  assert.equal(m.requests.length, 4, 'must stop at total_pages and never ask for a 4th page')
  assert.deepEqual(m.requests.slice(1).map(r => r.params), [1, 2, 3].map(page => ({ platform: 'codeforces', page, page_size: 100 })))
  assert.equal(m.rows.value.length, 205, 'table count must be the fully collected total, not one page')
  assert.equal(m.pagedRows.value.length, 20, 'table renders 20 rows per page')
  m.tablePage.value = 11
  assert.equal(m.pagedRows.value.length, 5); assert.equal(m.pagedRows.value[0].id, 201)
  m.tablePage.value = 1
  assert.equal(m.chartPoints.value.length, 205, 'chart must keep every row, not the visible page')
  assert.equal(m.unexcludedCount.value, 202)
  await settle(m, 0, response(scoreRows(100), 1, 300, 3))
  assert.equal(m.requests.length, 4, 'the superseded run must not fetch its own page 2')
  assert.equal(m.rows.value.length, 205, 'the superseded run must not clear the published collection')
  assert.doesNotMatch(m.source, /计入积分场数|countedCount|\.perf\b/)
  assert.match(m.source, /未排除记录/); assert.match(m.source, /不等同于计分场数/)
})

test('MyScores: platform switch clears rows and resets the table page synchronously', async t => {
  const m = mount('MyScores'); t.after(() => m.stop())
  await settle(m, 0, response(scoreRows(25)))
  assert.equal(m.rows.value.length, 25)
  m.tablePage.value = 2
  m.platform.value = 'atcoder'
  assert.equal(m.rows.value.length, 0, 'switching platform must drop the old platform rows in the same tick')
  assert.equal(m.tablePage.value, 1, 'switching platform must send the table back to page 1')
  assert.equal(m.pagedRows.value.length, 0)
  assert.equal(m.unexcludedCount.value, 0, 'metrics must not keep counting the previous platform')
  assert.equal(m.loading.value, true)
  assert.equal(m.requests.length, 2)
})

test('MyScores: stale intermediate page never publishes or requests another page', async t => {
  const m = mount('MyScores'); t.after(() => m.stop())
  await settle(m, 0, response(scoreRows(100), 1, 300, 3)); assert.equal(m.requests.length, 2)
  m.platform.value = 'atcoder'; await tick()
  assert.equal(m.requests.length, 3, 'a live switch refetches without waiting for the stale page')
  await settle(m, 1, response(scoreRows(100, 101), 2, 300, 3))
  assert.equal(m.requests.length, 3, 'the stale page-2 run must not continue to page 3')
  assert.equal(m.rows.value.length, 0)
  assert.equal(m.loading.value, true, 'the live request stays loading while a superseded page lands')
  await settle(m, 2, response(scoreRows(7), 1, 7, 1))
  assert.equal(m.rows.value.length, 7)
  assert.equal(m.loading.value, false)
})

test('MyScores: intermediate page error publishes no partial total', async t => {
  const m = mount('MyScores'); t.after(() => m.stop())
  await settle(m, 0, response(scoreRows(100), 1, 101, 2)); assert.equal(m.requests.length, 2)
  m.requests[1].reject(new Error('page 2 down')); await tick()
  assert.equal(m.rows.value.length, 0, 'a failed collection must not publish page 1 alone')
  assert.equal(m.unexcludedCount.value, 0)
  assert.equal(m.totalDelta.value, 0)
  assert.match(m.error.value, /加载失败/)
  assert.equal(m.loading.value, false)
  assert.equal(m.requests.length, 2, 'a failure must not silently spawn another request')
})

for (const field of ['platform', 'rated', 'keyword']) {
  test(`Contests: ${field} resets to page 1 synchronously and sends one request`, async t => {
    const m = mount('Contests'); t.after(() => m.stop())
    await settle(m, 0, response([{ id: 'loaded' }], 1, 40))
    assert.equal(m.rows.value.length, 1)
    m.page.value = 3; await tick()
    assert.equal(m.requests.length, 1, 'page is not a resource input — pagination goes through onPage')
    m[field].value = ({ platform: 'atcoder', rated: 'yes', keyword: 'abc' })[field]
    assert.equal(m.page.value, 1, 'filter change must reset the page synchronously')
    assert.equal(m.rows.value.length, 0, 'filter change must clear the previous results synchronously')
    assert.equal(m.total.value, 0)
    await tick(); m.advance(300); await tick()
    assert.equal(m.requests.length, 2, 'one filter change = exactly one request')
    const sent = m.requests.at(-1).params
    assert.equal(sent.page, 1)
    assert.equal(sent.platform, field === 'platform' ? 'atcoder' : undefined)
    assert.equal(sent.is_rated, field === 'rated' ? true : undefined)
    assert.equal(sent.name, field === 'keyword' ? 'abc' : undefined)
  })
}

test('Contests: typing immediately invalidates old success and debounces 300ms', async t => {
  const m = mount('Contests'); t.after(() => m.stop())
  m.keyword.value = 'a'
  assert.equal(m.requests.length, 1, 'keyword input must wait for the debounce before sending')
  assert.equal(m.timers.size, 1, 'keyword input must schedule exactly one timer')
  await settle(m, 0, response([{ id: 'old' }], 1, 10))
  assert.equal(m.rows.value.length, 0, 'typing must invalidate the in-flight response at once')
  assert.equal(m.loading.value, true)
  assert.equal(m.requests.length, 1); m.advance(299); assert.equal(m.requests.length, 1)
  m.keyword.value = 'ab'; await tick(); m.advance(299); assert.equal(m.requests.length, 1)
  assert.equal(m.timers.size, 1, 'the second keystroke must replace the pending timer, not stack it')
  m.advance(1); await tick()
  assert.equal(m.requests.length, 2, 'a burst of keystrokes must collapse into one request')
  assert.equal(m.requests[1].params.name, 'ab', 'the surviving request must carry the last keyword')
})

test('Contests: typing immediately invalidates old error', async t => {
  const m = mount('Contests'); t.after(() => m.stop())
  m.keyword.value = 'a'
  m.requests[0].reject(new Error('old')); await tick()
  assert.equal(m.error.value, '', 'the superseded failure must not surface an error')
  assert.equal(m.loading.value, true)
  assert.equal(m.requests.length, 1, 'an invalidating keystroke must not send a second request')
})

test('Contests: rapid pagination keeps only newest page', async t => {
  const m = mount('Contests'); t.after(() => m.stop())
  m.onPage(2); m.onPage(3)
  assert.equal(m.requests.length, 3, 'onPage must reload once per page change')
  assert.deepEqual(m.requests.map(r => r.params.page), [1, 2, 3])
  await settle(m, 2, response([{ id: 3 }], 1, 30))
  assert.equal(m.rows.value[0].id, 3); assert.equal(m.total.value, 30)
  await settle(m, 1, response([{ id: 2 }], 1, 20))
  await settle(m, 0, response([{ id: 1 }], 1, 12))
  assert.deepEqual(m.rows.value.map(r => r.id), [3], 'older pages must never overwrite the newest page')
  assert.equal(m.total.value, 30)
  assert.equal(m.page.value, 3)
})

test('Contests: local sort neither requests nor resets page and labels disclose scope', async t => {
  const m = mount('Contests'); t.after(() => m.stop())
  m.onPage(2)
  await settle(m, 1, response([{ id: 1, difficulty_factor: 1 }, { id: 2, difficulty_factor: 3 }]))
  const before = m.requests.length
  m.sort.value = 'difficulty'; await tick()
  assert.equal(m.requests.length, before, 'sort is page-local — must not hit the API')
  assert.equal(m.page.value, 2, 'sort must not reset pagination')
  assert.equal(m.sortedRows.value[0].id, 2)
  assert.ok(m.sortOptions.length >= 2, 'sort options must exist')
  assert.ok(m.sortOptions.every(o => o.label.startsWith('本页')),
    `sort labels must disclose the page scope, got: ${m.sortOptions.map(o => o.label).join(' / ')}`)
})

test('Contests: changing platform during debounce cancels duplicate search request', async t => {
  const m = mount('Contests'); t.after(() => m.stop())
  m.keyword.value = 'abc'; await tick()
  assert.equal(m.requests.length, 1, 'keyword alone is debounced')
  m.platform.value = 'atcoder'; await tick()
  assert.equal(m.timers.size, 0, 'a non-debounced input must cancel the pending search timer')
  assert.equal(m.requests.length, 2, 'the platform switch replaces the pending search request')
  m.advance(300); await tick()
  assert.equal(m.requests.length, 2, 'the cancelled timer must not fire a duplicate request')
  assert.equal(m.requests[1].params.name, 'abc')
  assert.equal(m.requests[1].params.platform, 'atcoder')
})

test('Contests: unmount clears search timer', async () => {
  const m = mount('Contests')
  m.keyword.value = 'abc'; await tick()
  assert.equal(m.timers.size, 1, 'a pending search timer must exist before unmount')
  m.stop()
  assert.equal(m.timers.size, 0, 'unmount must clear the pending timer')
  m.advance(300); await tick()
  assert.equal(m.requests.length, 1, 'no request may be sent after unmount')
})
