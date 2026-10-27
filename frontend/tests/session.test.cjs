const { test } = require('node:test')
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const axios = require('axios')

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function harness(path, imports, extras = {}) {
  const values = new Map([['access_token', 'initial-access'], ['refresh_token', 'initial-refresh'], ['auth_source', 'local']])
  const localStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
  const events = []
  const modules = new Map()
  function load(file) {
    if (modules.has(file)) return modules.get(file)
    const module = { exports: {} }
    const source = readFileSync(resolve(__dirname, '../src', file), 'utf8').replace(/import\.meta\.env\.VITE_PASSPORT_URL/g, '"https://identity.example.test"')
    const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } })
    vm.runInNewContext(outputText, { module, exports: module.exports, require: name => {
      if (name === './session' || name === '@/api/session') return load('api/session.ts')
      assert.ok(name in imports, `Unexpected import: ${name}`)
      return imports[name]
    }, localStorage, window: { dispatchEvent: e => events.push(e.type) }, Event, AbortSignal, crypto: require('node:crypto').webcrypto, ...extras })
    modules.set(file, module.exports)
    return module.exports
  }
  return { exports: load(path), session: load('api/session.ts'), localStorage, values, events }
}

function clientHarness(retryFails = false) {
  const refresh = deferred()
  let refreshCalls = 0
  const context = harness('api/client.ts', {
    axios: { ...axios, create: () => axios.create({ adapter: async config => {
      if (!config._retry || retryFails) throw new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, { status: 401, data: {}, headers: {}, statusText: 'Unauthorized', config })
      return { status: 200, data: 'ok', headers: {}, statusText: 'OK', config }
    } }), post: () => { refreshCalls++; return refresh.promise } },
    '../utils/device': { getDeviceId: () => 'test-device' },
  })
  return { ...context, refresh, client: context.exports.default, refreshCalls: () => refreshCalls }
}

async function startRequests(context) {
  const requests = ['/first', '/second', '/third'].map(url => context.client.get(url).then(() => 'fulfilled', () => 'rejected'))
  await new Promise(setImmediate)
  assert.equal(context.refreshCalls(), 1)
  return requests
}

async function settledWithin(requests) {
  let timer
  const result = await Promise.race([Promise.all(requests), new Promise(resolve => { timer = setTimeout(() => resolve('pending'), 200) })])
  clearTimeout(timer)
  return result
}

test('concurrent 401 responses share one successful refresh', async () => {
  const h = clientHarness()
  const requests = await startRequests(h)
  h.refresh.resolve({ data: { access: 'renewed-access', refresh: 'renewed-refresh' } })
  assert.deepEqual(await settledWithin(requests), ['fulfilled', 'fulfilled', 'fulfilled'])
  assert.equal(h.localStorage.getItem('access_token'), 'renewed-access')
  assert.equal(h.refreshCalls(), 1)
})

test('failed refresh rejects every waiter instead of leaving loading pending', async () => {
  const h = clientHarness()
  const requests = await startRequests(h)
  h.refresh.reject(new Error('Refresh rejected'))
  assert.deepEqual(await settledWithin(requests), ['rejected', 'rejected', 'rejected'])
  assert.equal(h.localStorage.getItem('access_token'), null)
  assert.equal(h.events.length, 1)
})

test('late refresh cannot restore a logged-out session', async () => {
  const h = clientHarness()
  const requests = await startRequests(h)
  h.session.clearSession()
  h.refresh.resolve({ data: { access: 'obsolete-access', refresh: 'obsolete-refresh' } })
  assert.deepEqual(await settledWithin(requests), ['rejected', 'rejected', 'rejected'])
  assert.equal(h.localStorage.getItem('access_token'), null)
  assert.equal(h.events.length, 0)
})

test('failure of an old refresh cannot erase a newly signed-in session', async () => {
  const h = clientHarness()
  const requests = await startRequests(h)
  h.session.saveSession('new-session-access', 'new-session-refresh', 'local')
  h.refresh.reject(new Error('Old session expired'))
  assert.deepEqual(await settledWithin(requests), ['rejected', 'rejected', 'rejected'])
  assert.equal(h.localStorage.getItem('access_token'), 'new-session-access')
  assert.equal(h.events.length, 0)
})

test('queued retries cannot recursively refresh rejected credentials', async () => {
  const h = clientHarness(true)
  const requests = await startRequests(h)
  h.refresh.resolve({ data: { access: 'renewed-access' } })
  assert.deepEqual(await settledWithin(requests), ['rejected', 'rejected', 'rejected'])
  assert.equal(h.refreshCalls(), 1)
})

test('late 401 from a previous account cannot refresh or replay using the new account', async () => {
  const h = clientHarness()
  const reply = deferred()
  let config
  h.client.defaults.adapter = request => { config = request; return reply.promise }
  const request = h.client.post('/action', { id: 1 }).then(() => 'fulfilled', () => 'rejected')
  await new Promise(setImmediate)
  h.session.saveSession('new-session-access', 'new-session-refresh', 'local')
  reply.reject(new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, { status: 401, data: {}, config }))
  assert.deepEqual(await settledWithin([request]), ['rejected'])
  assert.equal(h.refreshCalls(), 0)
  assert.equal(h.localStorage.getItem('access_token'), 'new-session-access')
  assert.equal(h.events.length, 0)
})

test('late successful data from the previous account is discarded', async () => {
  const h = clientHarness()
  const reply = deferred()
  let config
  h.client.defaults.adapter = request => { config = request; return reply.promise }
  const request = h.client.get('/me').then(() => 'fulfilled', () => 'rejected')
  await new Promise(setImmediate)
  h.session.clearSession()
  reply.resolve({ config, status: 200, data: { id: 1 }, headers: {}, statusText: 'OK' })
  assert.deepEqual(await settledWithin([request]), ['rejected'])
})

test('another tab refreshing the same session does not cancel successful operations', async () => {
  const h = clientHarness()
  const reply = deferred()
  let config
  h.client.defaults.adapter = request => { config = request; return reply.promise }
  const request = h.client.post('/action', { id: 1 }).then(() => 'fulfilled', () => 'rejected')
  await new Promise(setImmediate)
  h.localStorage.setItem('access_token', 'another-tab-access')
  h.localStorage.setItem('refresh_token', 'another-tab-refresh')
  reply.resolve({ config, status: 200, data: { ok: true }, headers: {}, statusText: 'OK' })
  assert.deepEqual(await settledWithin([request]), ['fulfilled'])
  assert.equal(h.refreshCalls(), 0)
})

test('failure of an old refresh rejects every waiter as cancelled after switching accounts', async () => {
  const h = clientHarness()
  const requests = ['/me/', '/other/'].map(url => h.client.get(url).then(() => false, error => axios.isCancel(error)))
  await new Promise(setImmediate)
  h.session.saveSession('new-session-access', 'new-session-refresh', 'local')
  h.refresh.reject(new Error('Old refresh failed'))
  assert.deepEqual(await settledWithin(requests), [true, true])
  assert.equal(h.localStorage.getItem('access_token'), 'new-session-access')
  assert.equal(h.events.length, 0)
})

test('another tab completing refresh prevents an old refresh failure from clearing the session', async () => {
  const h = clientHarness()
  const requests = await startRequests(h)
  h.localStorage.setItem('access_token', 'another-tab-access')
  h.localStorage.setItem('refresh_token', 'another-tab-refresh')
  h.refresh.reject(new Error('Refresh raced with another tab'))
  assert.deepEqual(await settledWithin(requests), ['fulfilled', 'fulfilled', 'fulfilled'])
  assert.equal(h.localStorage.getItem('access_token'), 'another-tab-access')
  assert.equal(h.events.length, 0)
})

test('logout clears local state before waiting for remote revocation', async () => {
  const revoke = deferred()
  const h = harness('stores/auth.ts', {
    pinia: { defineStore: (_, setup) => setup },
    vue: { ref: value => ({ value }), computed: get => ({ get value() { return get() } }) },
    '@/api': { fetchMe: async () => ({ id: 1 }), login: async () => {} },
    '@/composables/useToast': { toast: () => {} },
  }, { fetch: () => revoke.promise })
  const store = h.exports.useAuthStore()
  store.authSource.value = 'passport'
  const logout = store.logout()
  assert.equal(h.localStorage.getItem('access_token'), null)
  assert.equal(store.token.value, null)
  assert.notEqual(await settledWithin([Promise.resolve(logout)]), 'pending')
  revoke.resolve({ ok: true })
  await logout
})

for (const failure of ['network', 'http']) {
  test(`remote revocation ${failure} failure is visible without restoring local state`, async () => {
    const messages = []
    const h = harness('stores/auth.ts', {
      pinia: { defineStore: (_, setup) => setup },
      vue: { ref: value => ({ value }), computed: get => ({ get value() { return get() } }) },
      '@/api': { fetchMe: async () => ({ id: 1 }), login: async () => {} },
      '@/composables/useToast': { toast: message => messages.push(message) },
    }, { fetch: () => failure === 'http' ? Promise.resolve({ ok: false }) : Promise.reject(new Error('Offline')) })
    const store = h.exports.useAuthStore()
    store.authSource.value = 'passport'
    store.logout()
    await new Promise(setImmediate)
    assert.equal(messages.length, 1)
    assert.equal(h.localStorage.getItem('access_token'), null)
  })
}

test('logout revokes the latest refreshed access token rather than stale store state', async () => {
  let authorization
  const h = harness('stores/auth.ts', {
    pinia: { defineStore: (_, setup) => setup },
    vue: { ref: value => ({ value }), computed: get => ({ get value() { return get() } }) },
    '@/api': { fetchMe: async () => ({ id: 1 }), login: async () => {} },
    '@/composables/useToast': { toast: () => {} },
  }, { fetch: (_, options) => { authorization = options.headers.Authorization; return Promise.resolve({ ok: true }) } })
  const store = h.exports.useAuthStore()
  store.authSource.value = 'passport'
  h.localStorage.setItem('access_token', 'refreshed-access')
  store.logout()
  assert.equal(authorization, 'Bearer refreshed-access')
})

test('cancelled navigation from an old session does not log out a new session', async () => {
  let guard
  let logouts = 0
  harness('router/index.ts', {
    'vue-router': { createWebHistory: () => ({}), createRouter: () => ({ beforeEach: fn => { guard = fn } }) },
    axios,
    '@/stores/auth': { useAuthStore: () => ({ token: 'new-access', user: null, loadMe: () => Promise.reject(new axios.CanceledError('Old session')), logout: () => { logouts++ } }) },
  })
  assert.equal(await guard({ name: 'members' }), false)
  assert.equal(logouts, 0)
})
