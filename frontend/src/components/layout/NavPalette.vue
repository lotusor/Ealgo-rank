<script setup lang="ts">
/**
 * 「全部功能」面板 —— 导航收纳的载体。
 *
 * 两种用法共用同一份内容：
 *  - 桌面：作为 Popover 的面板（点「全部功能」展开）；
 *  - 移动端：直接作为汉堡抽屉的内容（≤768px 选项卡条隐藏时）。
 *
 * 交互：勾选即固定到顶部；已固定的项可拖拽排序，也可用上下箭头按钮
 * 排序（键盘/无障碍可达，不依赖拖拽）。
 */
import { computed, ref } from 'vue'
import type { NavGroup, NavItem } from '@/config/navRegistry'

const props = defineProps<{
  /** 当前身份可见的全部功能项（按分组） */
  sections: { group: NavGroup; items: NavItem[] }[]
  /** 已固定在顶部的键，顺序即展示顺序 */
  pinnedKeys: string[]
  maxTabs: number
}>()

const emit = defineEmits<{
  toggle: [key: string]
  'move-by': [key: string, delta: number]
  'move-to': [fromKey: string, toKey: string]
  reset: []
  navigate: [key: string]
}>()

const byKey = computed(() => {
  const map = new Map<string, NavItem>()
  props.sections.forEach((s) => s.items.forEach((i) => map.set(i.key, i)))
  return map
})

const pinnedItems = computed<NavItem[]>(() =>
  props.pinnedKeys
    .map((k) => byKey.value.get(k))
    .filter((i): i is NavItem => Boolean(i)),
)

/** 未固定的项，按分组展示 */
const unpinnedSections = computed(() =>
  props.sections
    .map((s) => ({
      group: s.group,
      items: s.items.filter((i) => !props.pinnedKeys.includes(i.key)),
    }))
    .filter((s) => s.items.length > 0),
)

const dragKey = ref<string | null>(null)
const overKey = ref<string | null>(null)

function onDragStart(key: string, e: DragEvent) {
  dragKey.value = key
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', key)
  }
}
function onDrop(targetKey: string) {
  if (dragKey.value && dragKey.value !== targetKey) {
    emit('move-to', dragKey.value, targetKey)
  }
  dragKey.value = null
  overKey.value = null
}
function onDragEnd() {
  dragKey.value = null
  overKey.value = null
}
</script>

<template>
  <div class="palette">
    <div class="palette-head">
      <div>
        <div class="palette-title">全部功能</div>
        <div class="palette-hint">
          固定在顶部的功能显示为选项卡，最多 {{ maxTabs }} 个
        </div>
      </div>
      <button class="palette-reset" type="button" @click="emit('reset')">
        恢复默认
      </button>
    </div>

    <div class="palette-section-label">
      已固定在顶部（{{ pinnedItems.length }}/{{ maxTabs }}）
    </div>
    <ul class="palette-list">
      <li
        v-for="(item, index) in pinnedItems"
        :key="item.key"
        class="palette-row is-pinned"
        :class="{ 'is-dragging': dragKey === item.key, 'is-over': overKey === item.key }"
        draggable="true"
        @dragstart="onDragStart(item.key, $event)"
        @dragover.prevent="overKey = item.key"
        @dragleave="overKey = null"
        @drop.prevent="onDrop(item.key)"
        @dragend="onDragEnd"
      >
        <span class="palette-grip" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <circle cx="9" cy="6" r="1.6" />
            <circle cx="15" cy="6" r="1.6" />
            <circle cx="9" cy="12" r="1.6" />
            <circle cx="15" cy="12" r="1.6" />
            <circle cx="9" cy="18" r="1.6" />
            <circle cx="15" cy="18" r="1.6" />
          </svg>
        </span>
        <span class="palette-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path :d="item.icon" />
          </svg>
        </span>
        <span class="palette-label">{{ item.label }}</span>
        <span class="palette-actions">
          <button
            class="palette-icon-btn"
            type="button"
            title="上移"
            aria-label="上移"
            :disabled="index === 0"
            @click="emit('move-by', item.key, -1)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6" /></svg>
          </button>
          <button
            class="palette-icon-btn"
            type="button"
            title="下移"
            aria-label="下移"
            :disabled="index === pinnedItems.length - 1"
            @click="emit('move-by', item.key, 1)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6" /></svg>
          </button>
          <button
            class="palette-chip"
            type="button"
            @click="emit('toggle', item.key)"
          >
            移除
          </button>
        </span>
      </li>
    </ul>

    <template v-for="section in unpinnedSections" :key="section.group.key">
      <div class="palette-section-label">{{ section.group.label }}</div>
      <ul class="palette-list">
        <li
          v-for="item in section.items"
          :key="item.key"
          class="palette-row"
        >
          <span class="palette-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="item.icon" />
            </svg>
          </span>
          <button
            class="palette-main"
            type="button"
            :title="`打开${item.label}`"
            @click="emit('navigate', item.key)"
          >
            <span class="palette-label">{{ item.label }}</span>
            <span class="palette-desc">{{ item.desc }}</span>
          </button>
          <button
            class="palette-chip"
            type="button"
            @click="emit('toggle', item.key)"
          >
            固定
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.palette {
  padding: var(--space-3);
}
.palette-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3) var(--space-3);
  border-bottom: 1px solid var(--color-border);
}
.palette-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.palette-hint {
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.palette-reset {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
}
.palette-section-label {
  padding: var(--space-4) var(--space-3) var(--space-2);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-text-tertiary);
}
.palette-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.palette-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  transition: background var(--duration-fast) var(--ease-standard);
}
.palette-row:hover {
  background: var(--color-bg-overlay);
}
.palette-row.is-pinned {
  cursor: grab;
}
.palette-row.is-dragging {
  opacity: 0.5;
}
.palette-row.is-over {
  box-shadow: inset 0 2px 0 0 var(--color-primary);
}
.palette-grip {
  flex-shrink: 0;
  display: inline-flex;
  color: var(--color-text-disabled);
}
.palette-grip svg {
  width: 14px;
  height: 14px;
}
.palette-icon {
  flex-shrink: 0;
  display: inline-flex;
  color: var(--color-text-tertiary);
}
.palette-icon svg {
  width: 16px;
  height: 16px;
}
.palette-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  padding: 0;
}
.palette-label {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.palette-desc {
  font-size: 12px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.palette-row:hover .palette-label {
  color: var(--color-text-primary);
}
.palette-actions {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.palette-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  background: none;
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}
.palette-icon-btn svg {
  width: 14px;
  height: 14px;
}
.palette-icon-btn:hover:not(:disabled) {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}
.palette-icon-btn:disabled {
  opacity: 0.35;
  cursor: default;
}
.palette-chip {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}
.palette-chip:hover {
  border-color: var(--color-border-focus);
  color: var(--color-text-primary);
}
</style>
