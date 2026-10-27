const { test } = require('node:test')
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const vue = require('vue')

function loadUseResource() {
  const source = readFileSync(resolve(__dirname, '../src/composables/useResource.ts'), 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  })
  const unmounts = []
  const module = { exports: {} }
  vm.runInNewContext(outputText, {
    module,
    exports: module.exports,
    setTimeout,
    clearTimeout,
    require: (name) => {
      if (name !== 'vue') throw new Error(`Unexpected import: ${name}`)
      return { ...vue, onBeforeUnmount: (fn) => unmounts.push(fn) }
    },
  })
  return { useResource: module.exports.useResource, unmounts }
}

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const tick = async (n = 6) => { for (let i = 0; i < n; i++) { await Promise.resolve(); await vue.nextTick() } }

function harness(loader, options = {}) {
  const { useResource, unmounts } = loadUseResource()
  const scope = vue.effectScope()
  let resource
  scope.run(() => { resource = useResource(loader, { initial: null, ...options }) })
  return { ...resource, unmounts, stop: () => scope.stop() }
}

test('publishes the newest response even when the older one lands last', async () => {
  const first = deferred()
  const second = deferred()
  const queue = [first.promise, second.promise]
  let call = 0
  const r = harness(() => queue[call++], { immediate: false })
  r.reload(); r.reload()
  await tick()
  second.resolve('newest')
  await tick()
  first.resolve('stale')
  await tick()
  assert.equal(r.data.value, 'newest')
  assert.equal(r.loading.value, false)
})

test('a stale failure cannot clear the loading state of the newer request', async () => {
  const first = deferred()
  const second = deferred()
  const queue = [first.promise, second.promise]
  let call = 0
  const r = harness(() => queue[call++], { immediate: false })
  r.reload(); r.reload()
  await tick()
  first.reject(new Error('stale'))
  await tick()
  assert.equal(r.loading.value, true, 'stale finally must not end the live request')
  assert.equal(r.error.value, null)
  second.resolve('live')
  await tick()
  assert.equal(r.data.value, 'live')
  assert.equal(r.loading.value, false)
})

test('error path resets to initial and reports once', async () => {
  const reported = []
  const r = harness(() => Promise.reject(new Error('offline')), { initial: 'seed', onError: (e) => reported.push(e.message) })
  await tick()
  assert.equal(r.data.value, 'seed')
  assert.equal(r.error.value.message, 'offline')
  assert.equal(r.loading.value, false)
  assert.deepEqual(reported, ['offline'])
})

test('input change invalidates in flight immediately and collapses debounced bursts', async () => {
  const keyword = vue.ref('')
  const calls = []
  const pending = []
  const r = harness(({ isCurrent }) => {
    calls.push(keyword.value)
    const d = deferred()
    pending.push(d)
    return d.promise.then((v) => (isCurrent() ? v : null))
  }, { initial: [], watch: [keyword], debounce: 300 })
  await tick()
  assert.deepEqual(calls, [''], 'immediate run happens once')

  keyword.value = 'a'
  await tick()
  assert.equal(r.loading.value, true, 'typing shows loading without waiting for the debounce')
  assert.equal(r.data.value.length, 0, 'stale rows cleared synchronously')
  keyword.value = 'ab'
  await tick()
  assert.equal(pending.length, 1, 'debounce must not fire a request per keystroke')
  await new Promise(res => setTimeout(res, 320))
  await tick()
  assert.deepEqual(calls, ['', 'ab'])
  pending[pending.length - 1].resolve(['row'])
  await tick()
  assert.deepEqual(r.data.value, ['row'])
  assert.equal(r.loading.value, false)
  r.stop()
})

test('reset hook runs on every input change', async () => {
  const platform = vue.ref('')
  const tablePage = vue.ref(3)
  const calls = []
  const r = harness(async () => { calls.push(platform.value); return [] }, {
    initial: [],
    watch: [platform],
    reset: () => { tablePage.value = 1 },
  })
  await tick()
  platform.value = 'codeforces'
  await tick()
  assert.equal(tablePage.value, 1)
  assert.deepEqual(calls, ['', 'codeforces'])
  r.stop()
})

test('unmount invalidates a pending response', async () => {
  const d = deferred()
  const r = harness(() => d.promise, { initial: 'seed' })
  await tick()
  // 组件生命周期钩子不会随 effectScope.stop() 触发，这里显式跑一遍
  r.unmounts.forEach((fn) => fn())
  d.resolve('late')
  await tick()
  assert.equal(r.data.value, 'seed', 'unmounted resource must not write state')
})
