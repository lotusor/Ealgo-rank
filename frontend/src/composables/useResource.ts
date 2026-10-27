import { onBeforeUnmount, ref, watch, type Ref, type WatchSource } from 'vue'

/** 传给 loader 的上下文：每次 await 之后都要问一次，过期响应不得发布。 */
export interface ResourceContext {
  isCurrent: () => boolean
}

export interface ResourceOptions<T> {
  /** 输入变化即作废在途请求、清回 initial 并重新加载 */
  watch?: WatchSource[]
  /**
   * 输入类请求的防抖毫秒。传函数可按「这次变了哪个输入」决定：
   * 例如搜索框要防抖，而点平台按钮必须立刻出结果。
   */
  debounce?: number | ((values: unknown[], previous: unknown[] | undefined) => number)
  /** 每次（含防抖等待期）都会先写回这个值，避免把上一个输入的半截数据当当前结果 */
  initial: T
  /** 输入变化时的额外复位（例如把表页退回第 1 页） */
  reset?: () => void
  immediate?: boolean
  onError?: (error: unknown) => void
}

export interface Resource<T> {
  data: Ref<T>
  loading: Ref<boolean>
  error: Ref<unknown>
  reload: () => Promise<void>
}

/**
 * 列表/详情请求的生命周期收口：序号作废、四态、防抖、卸载失效。
 *
 * 迁移前每个页面各自手写 `requestSeq` + `loading` + `error`，漏一处就会出现
 * 「切平台显示上一个平台的数据」或「失败被 catch 吞掉后停在旧列表」。
 */
export function useResource<T>(
  loader: (context: ResourceContext) => Promise<T>,
  options: ResourceOptions<T>,
): Resource<T> {
  const { watch: sources = [], debounce = 0, initial, reset, immediate = true, onError } = options

  const data = ref(initial) as Ref<T>
  const loading = ref(false)
  const error = ref<unknown>(null)
  let seq = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  async function run() {
    const current = ++seq
    const isCurrent = () => current === seq
    loading.value = true
    error.value = null
    try {
      const result = await loader({ isCurrent })
      // 过期响应连 loading 都不能改，否则旧请求的 finally 会掐掉新请求的加载态
      if (!isCurrent()) return
      data.value = result
    } catch (e) {
      if (!isCurrent()) return
      data.value = initial
      error.value = e
      onError?.(e)
    } finally {
      if (isCurrent()) loading.value = false
    }
  }

  /** 输入变化：立刻作废在途请求并清回初值，防抖只推迟「发新请求」。 */
  function invalidate() {
    seq += 1
    if (timer !== undefined) {
      clearTimeout(timer)
      timer = undefined
    }
    data.value = initial
    error.value = null
    loading.value = true
    reset?.()
  }

  function schedule(values?: unknown[], previous?: unknown[]) {
    invalidate()
    const ms = typeof debounce === 'function' ? debounce(values ?? [], previous) : debounce
    if (ms > 0) timer = setTimeout(run, ms)
    else void run()
  }

  if (sources.length) {
    watch(sources, (values, previous) => schedule(values, previous), { flush: 'sync' })
  }

  onBeforeUnmount(() => {
    seq += 1
    if (timer !== undefined) clearTimeout(timer)
  })

  if (immediate) void run()

  return { data, loading, error, reload: run }
}
