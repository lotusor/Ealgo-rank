<script setup lang="ts">
import { computed } from 'vue'

/**
 * 原型 renderPagination 的可用版本。
 *
 * 原型有两个真问题，这里都修掉了：
 *  1. 调用方全部传 `p=>{}` 空回调，且列表数据从不按当前页切片
 *     → 点页码只有高亮变化，表格内容一动不动。这里改成受控组件，
 *       页码变化必须由父组件重新取数，翻页才真的生效。
 *  2. `for(let i=1;i<=total;i++)` 无脑铺完所有页码。
 *     真实数据几百页时分页条会横着撑爆容器。这里做首尾 + 当前页窗口 + 省略号。
 */
const props = withDefaults(
  defineProps<{
    page: number
    pageSize: number
    total: number
    /** 是否显示"第 x–y 条 / 共 n 条" */
    showMeta?: boolean
    /** 当前页两侧各展开几个页码 */
    siblings?: number
  }>(),
  { showMeta: true, siblings: 1 },
)

const emit = defineEmits<{ 'update:page': [value: number] }>()

const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.total / Math.max(1, props.pageSize))),
)

type Item = { type: 'page'; value: number } | { type: 'gap'; key: string }

const items = computed<Item[]>(() => {
  const last = totalPages.value
  const cur = Math.min(Math.max(1, props.page), last)
  const s = props.siblings

  // 页数不多时直接全铺，省得出现 1 … 2 这种滑稽结果
  if (last <= 5 + s * 2) {
    return Array.from({ length: last }, (_, i) => ({
      type: 'page' as const,
      value: i + 1,
    }))
  }

  const from = Math.max(2, cur - s)
  const to = Math.min(last - 1, cur + s)
  const out: Item[] = [{ type: 'page', value: 1 }]
  if (from > 2) out.push({ type: 'gap', key: 'head' })
  for (let i = from; i <= to; i++) out.push({ type: 'page', value: i })
  if (to < last - 1) out.push({ type: 'gap', key: 'tail' })
  out.push({ type: 'page', value: last })
  return out
})

const rangeFrom = computed(() =>
  props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1,
)
const rangeTo = computed(() =>
  Math.min(props.total, props.page * props.pageSize),
)

function go(p: number) {
  const next = Math.min(Math.max(1, p), totalPages.value)
  if (next !== props.page) emit('update:page', next)
}
</script>

<template>
  <div v-if="totalPages > 1 || showMeta" class="pagination">
    <button
      type="button"
      class="page-btn"
      :disabled="page <= 1"
      aria-label="上一页"
      @click="go(page - 1)"
    >
      ‹
    </button>

    <template v-for="it in items" :key="it.type === 'page' ? it.value : it.key">
      <span v-if="it.type === 'gap'" class="page-ellipsis">…</span>
      <button
        v-else
        type="button"
        class="page-btn"
        :class="{ active: it.value === page }"
        :aria-current="it.value === page ? 'page' : undefined"
        @click="go(it.value)"
      >
        {{ it.value }}
      </button>
    </template>

    <button
      type="button"
      class="page-btn"
      :disabled="page >= totalPages"
      aria-label="下一页"
      @click="go(page + 1)"
    >
      ›
    </button>

    <span v-if="showMeta" class="page-meta">
      {{ rangeFrom }}–{{ rangeTo }} / {{ total }}
    </span>
  </div>
</template>
