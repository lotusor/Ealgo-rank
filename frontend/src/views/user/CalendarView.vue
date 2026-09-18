<script setup lang="ts">
/**
 * 竞赛日历。
 *
 * 当前进度（2026-09-18）：阶段 1 已落地**公开路由 + 页面外壳 + 视图切换**。
 * 完整功能（月历网格、三段式列表、筛选条、实时状态重算）在阶段 3 实现；
 * 其依赖的后端接口已在阶段 2 就绪：
 *   GET /api/v1/contests/?status=ongoing|upcoming|finished
 *                          &end_after=&end_before=&series=&search=&ordering=
 *   GET /api/v1/contests/meta/  （平台 / 系列 / 各状态计数 / 最近同步时间）
 */
import { ref } from 'vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

type CalendarViewMode = 'month' | 'list'

const view = ref<CalendarViewMode>('month')

const viewOptions = [
  { label: '月历', value: 'month' as const },
  { label: '列表', value: 'list' as const },
]
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">
          竞赛日历
          <span class="badge badge-info">开发中</span>
        </h1>
        <p class="page-subtitle">
          Codeforces · AtCoder · 牛客 三平台赛程，按时间维度浏览
        </p>
      </div>
      <SegmentedControl v-model="view" :options="viewOptions" />
    </div>

    <EmptyState
      title="赛程数据接入中"
      hint="页面外壳与视图切换已就绪，月历与赛事列表将在下一阶段上线。"
    />
  </div>
</template>
