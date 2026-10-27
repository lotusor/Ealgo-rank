const { test } = require('node:test')
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const ts = require('typescript')

function load(name, context = {}) {
  const source = readFileSync(resolve(__dirname, '../src/composables', name), 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  })
  const module = { exports: {} }
  const sandbox = { module, exports: module.exports, require, ...context }
  require('node:vm').runInNewContext(outputText, sandbox)
  return module.exports
}

function el(name, extra = {}) {
  return { name, tabIndex: 0, hasAttribute: () => false, getClientRects: () => [{}], ...extra }
}

test('nextFocusable wraps forward and backward', () => {
  const { nextFocusable } = load('focusTrap.ts')
  const [a, b, c] = [el('a'), el('b'), el('c')]
  const list = [a, b, c]
  assert.equal(nextFocusable(list, b, false), c)
  assert.equal(nextFocusable(list, c, false), a)
  assert.equal(nextFocusable(list, a, true), c)
  assert.equal(nextFocusable(list, b, true), a)
})

test('nextFocusable lands inside when focus escaped or list is empty', () => {
  const { nextFocusable } = load('focusTrap.ts')
  const [a, b] = [el('a'), el('b')]
  assert.equal(nextFocusable([a, b], null, false), a)
  assert.equal(nextFocusable([a, b], null, true), b)
  assert.equal(nextFocusable([a, b], el('outside'), false), a)
  assert.equal(nextFocusable([], el('outside'), false), null)
})

test('getFocusable drops disabled, hidden and negative-tabindex controls', () => {
  const { getFocusable } = load('focusTrap.ts')
  const kept = el('kept')
  const found = [kept, el('disabled', { hasAttribute: (n) => n === 'disabled' }),
    el('hidden', { getClientRects: () => [] }), el('negative', { tabIndex: -1 })]
  const root = { querySelectorAll: () => found }
  // 被测代码在独立 vm realm 内返回数组，跨 realm 原型不同，只能逐项比对
  const list = getFocusable(root)
  assert.equal(list.length, 1)
  assert.equal(list[0], kept)
  assert.equal(getFocusable(null).length, 0)
})

function documentStub() {
  const handlers = []
  return {
    handlers,
    addEventListener: (type, fn) => handlers.push({ type, fn }),
    removeEventListener: (type, fn) => {
      const i = handlers.findIndex(h => h.type === type && h.fn === fn)
      if (i >= 0) handlers.splice(i, 1)
    },
  }
}

test('overlay stack sends Escape to the topmost layer only and detaches when empty', () => {
  const document = documentStub()
  const { pushOverlay, popOverlay, overlayDepth } = load('overlayStack.ts', { document })
  const closed = []
  const outer = { requestClose: () => closed.push('outer') }
  const inner = { requestClose: () => closed.push('inner') }
  pushOverlay(outer)
  pushOverlay(inner)
  assert.equal(overlayDepth(), 2)
  document.handlers.find(h => h.type === 'keydown').fn({ key: 'Escape' })
  assert.deepEqual(closed, ['inner'])
  popOverlay(inner)
  document.handlers.find(h => h.type === 'keydown').fn({ key: 'Escape' })
  assert.deepEqual(closed, ['inner', 'outer'])
  popOverlay(outer)
  assert.equal(document.handlers.length, 0, 'listener must be removed once the stack is empty')
  popOverlay(outer)
  assert.equal(overlayDepth(), 0)
})

test('overlay stack ignores keys other than Escape', () => {
  const document = documentStub()
  const { pushOverlay } = load('overlayStack.ts', { document })
  let closed = 0
  pushOverlay({ requestClose: () => { closed += 1 } })
  document.handlers.find(h => h.type === 'keydown').fn({ key: 'Enter' })
  assert.equal(closed, 0)
})
