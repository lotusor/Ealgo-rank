<script setup lang="ts">
import { computed } from 'vue'

/**
 * 极简 Markdown 渲染：标题(#~####)/无序列表(- )/粗体(**x**)/行内代码(`x`)/段落。
 * 先做 HTML 转义再替换语法，内容安全（不引入第三方依赖，贴合自建设计系统）。
 */
const props = defineProps<{ source: string }>()

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function inline(s: string) {
  return s
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

const html = computed(() => {
  const lines = esc(props.source || '').split('\n')
  const out: string[] = []
  let inList = false
  for (const raw of lines) {
    const line = raw.trimEnd()
    const li = line.match(/^\s*[-*]\s+(.*)$/)
    const h = line.match(/^(#{1,4})\s+(.*)$/)
    if (li) {
      if (!inList) {
        out.push('<ul>')
        inList = true
      }
      out.push(`<li>${inline(li[1])}</li>`)
      continue
    }
    if (inList) {
      out.push('</ul>')
      inList = false
    }
    if (h) {
      const level = Math.min(h[1].length + 2, 6)
      out.push(`<h${level} class="md-h">${inline(h[2])}</h${level}>`)
    } else if (line.trim() !== '') {
      out.push(`<p>${inline(line)}</p>`)
    }
  }
  if (inList) out.push('</ul>')
  return out.join('\n')
})
</script>

<template>
  <div class="simple-md" v-html="html" />
</template>

<style scoped>
.simple-md {
  color: var(--color-text-secondary);
  line-height: 1.75;
  font-size: 14px;
}
.simple-md :deep(.md-h) {
  color: var(--color-text-primary);
  font-weight: 700;
  margin: var(--space-5) 0 var(--space-2);
}
.simple-md :deep(h3.md-h) { font-size: 17px; }
.simple-md :deep(h4.md-h) { font-size: 15px; }
.simple-md :deep(h5.md-h),
.simple-md :deep(h6.md-h) { font-size: 14px; }
.simple-md :deep(p) { margin: var(--space-2) 0; }
.simple-md :deep(ul) {
  margin: var(--space-2) 0;
  padding-left: 20px;
  list-style: disc;
}
.simple-md :deep(li) { margin: var(--space-1) 0; }
.simple-md :deep(strong) { color: var(--color-text-primary); }
.simple-md :deep(code) {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  font-size: 13px;
}
</style>
