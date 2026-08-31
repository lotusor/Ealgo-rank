<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getScoreRules } from '@/api'
import type { ScoreRules } from '@/api/types'
import SimpleMarkdown from '@/components/ui/SimpleMarkdown.vue'
import { platformName } from '@/utils/format'

const data = ref<ScoreRules | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    data.value = await getScoreRules()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载积分规则失败'
  } finally {
    loading.value = false
  }
})

function fmtFactor(v: string | number | null | undefined) {
  if (v == null) return '—'
  const n = typeof v === 'number' ? v : parseFloat(v)
  return isNaN(n) ? String(v) : n.toFixed(3)
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>用户端</span><span>/</span><span>积分规则</span></div>
        <h1 class="page-title">积分规则</h1>
        <p class="page-subtitle">总 rating 的加权公式与计算策略（系数调整后此处自动更新）</p>
      </div>
      <span v-if="data?.version" class="caption text-tertiary">规则版本 v{{ data.version }}</span>
    </div>

    <div v-if="error" class="alert"><span>{{ error }}</span></div>
    <div v-else-if="loading" class="card card-pad">
      <span class="skel" style="width: 40%; height: 24px" />
    </div>

    <template v-else-if="data">
      <div class="rules-grid">
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom: var(--space-3)">计算策略说明</div>
          <SimpleMarkdown
            :source="data.content || '规则内容准备中：各平台当前 rating × 平台系数，跨平台求和得到总 rating。详细说明即将上线。'"
          />
        </div>

        <div class="card card-pad" v-if="data.config">
          <div class="card-title" style="margin-bottom: var(--space-3)">当前生效系数（动态）</div>
          <table class="data-table" style="border: none">
            <thead>
              <tr><th>平台</th><th class="num-cell">平台系数</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in data.config.platforms" :key="p.platform">
                <td><span class="platform-tag" :class="p.platform === 'codeforces' ? 'cf' : p.platform === 'atcoder' ? 'atcoder' : p.platform === 'nowcoder' ? 'nowcoder' : ''">{{ platformName(p.platform) }}</span></td>
                <td class="num-cell num">{{ fmtFactor(p.factor) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="caption text-tertiary" style="margin-top: var(--space-4); line-height: 1.9">
            <div>平台系数权重：<b class="num">{{ fmtFactor(data.config.platform_weight) }}</b> · 比赛系数权重：<b class="num">{{ fmtFactor(data.config.contest_weight) }}</b>（两者之和为 1）</div>
            <div>比赛难度默认系数：<b class="num">{{ fmtFactor(data.config.default_contest_factor) }}</b></div>
            <div>每平台计分场次上限：<b class="num">{{ data.config.recent_contest_limit === 0 ? '不限制' : data.config.recent_contest_limit }}</b></div>
          </div>
        </div>
        <div class="card card-pad" v-else>
          <div class="card-title" style="margin-bottom: var(--space-3)">当前生效系数</div>
          <p class="body-sm text-tertiary">系数配置尚未初始化</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.rules-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
  align-items: start;
}
.alert {
  background: var(--color-danger-subtle);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}
@media (max-width: 980px) {
  .rules-grid { grid-template-columns: 1fr; }
}
</style>
