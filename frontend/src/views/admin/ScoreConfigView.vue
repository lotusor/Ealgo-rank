<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { listScoreConfigs, createScoreConfig, listDifficultyFactors, updateDifficultyFactor } from '@/api'
import type { ScoreConfig, ContestDifficultyFactor } from '@/api/types'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const loading = ref(false)
const saving = ref(false)

const empty: ScoreConfig = {
  id: 0,
  cf_factor: '1.000',
  atcoder_factor: '1.000',
  nowcoder_factor: '1.000',
  default_contest_factor: '1.000',
  platform_weight: '0.500',
  contest_weight: '0.500',
  recent_contest_limit: 5,
  rating_decay: '0.850',
  rating_prior: '1200.0',
  created_at: '',
  updated_at: '',
}

const form = reactive<ScoreConfig>({ ...empty })

// 比赛难度基线列表（平台 × 系列）
const difficultyFactors = ref<ContestDifficultyFactor[]>([])

async function load() {
  loading.value = true
  try {
    const res = await listScoreConfigs({ page: 1, page_size: 1 })
    if (res.results.length) {
      Object.assign(form, res.results[0])
    }
    const df = await listDifficultyFactors({ page_size: 100 })
    difficultyFactors.value = df.results
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '加载积分配置失败')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      cf_factor: form.cf_factor,
      atcoder_factor: form.atcoder_factor,
      nowcoder_factor: form.nowcoder_factor,
      recent_contest_limit: Number(form.recent_contest_limit) || 0,
      rating_decay: form.rating_decay,
      rating_prior: form.rating_prior,
    }
    const saved = await createScoreConfig(payload)
    Object.assign(form, saved)
    toast.success('积分配置已保存（下次重算榜单时全量生效）')
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onBaseBlur(item: ContestDifficultyFactor) {
  try {
    const payload: Record<string, unknown> = {
      platform: item.platform,
      series: item.series,
    }
    // 留空 = 回退代码默认表（perf_base 传 null）
    payload.perf_base = item.perf_base === null || (item.perf_base as unknown) === ''
      ? null
      : Number(item.perf_base)
    await updateDifficultyFactor(item.id, payload)
    toast.success(`已更新 ${item.platform_display} ${item.series} 难度基线`)
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '难度基线保存失败')
    load()
  }
}

const platformLabel = (p: string) =>
  p === 'codeforces' ? 'Codeforces' : p === 'atcoder' ? 'AtCoder' : '牛客'

onMounted(load)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>积分配置</span></div>
        <h1 class="page-title">积分配置设置</h1>
        <p class="page-subtitle">统一表现分算法（v3）：单场表现分 = 平台系数 ×（难度基线 D + 400 × 名次标准分）</p>
      </div>
    </div>

    <div v-if="loading" class="card card-pad body-sm text-tertiary">加载中…</div>

    <div v-else class="card card-pad" style="max-width: 720px">
      <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18M7 16l4-4 4 4 5-5" /></svg>
        站点 Rating 参数
      </div>
      <div class="grid-2">
        <div class="field">
          <label class="field-label">计分窗口（最近 N 场）</label>
          <input v-model.number="form.recent_contest_limit" class="input" type="number" min="1" step="1" />
          <p class="body-sm text-tertiary" style="margin-top: var(--space-2)">
            站点 Rating 取最近 N 场表现分的加权平均。
          </p>
        </div>
        <div class="field">
          <label class="field-label">评分衰减系数（0~1）</label>
          <input v-model="form.rating_decay" class="input" type="number" step="0.001" min="0" max="1" />
          <p class="body-sm text-tertiary" style="margin-top: var(--space-2)">
            最新一场权重 1，每往旧一场 ×该系数；越小越看重近期状态。
          </p>
        </div>
        <div class="field">
          <label class="field-label">新用户先验 Rating</label>
          <input v-model="form.rating_prior" class="input" type="number" step="1" min="0" />
          <p class="body-sm text-tertiary" style="margin-top: var(--space-2)">
            新账号的虚拟起点，随参赛场次快速淡出（防单场偶然极值）。
          </p>
        </div>
      </div>

      <div class="divider"></div>

      <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20" /></svg>
        平台系数（表现分乘数）
      </div>
      <p class="body-sm text-tertiary" style="margin-bottom: var(--space-4)">
        难度基线已按跨平台统一尺度标定，通常保持 1.0；仅在对某平台整体加权时调整。
      </p>
      <div class="grid-2">
        <div class="field">
          <label class="field-label">Codeforces</label>
          <input v-model="form.cf_factor" class="input" type="number" step="0.001" />
        </div>
        <div class="field">
          <label class="field-label">AtCoder</label>
          <input v-model="form.atcoder_factor" class="input" type="number" step="0.001" />
        </div>
        <div class="field">
          <label class="field-label">牛客</label>
          <input v-model="form.nowcoder_factor" class="input" type="number" step="0.001" />
        </div>
      </div>

      <div class="divider"></div>

      <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></svg>
        难度基线 D（平台 × 系列）
      </div>
      <p class="body-sm text-tertiary" style="margin-bottom: var(--space-4)">
        含义：预期排到该名次的水平值（rating 尺度）。留空使用系统默认表（CF Div.1≈2200 / Div.2≈1450、ABC≈800 / ARC≈1550 / AGC≈2400、牛客周赛≈950 等），改动后下次重算生效。
      </p>
      <div class="table-wrap" style="border: 1px solid var(--color-border); border-radius: var(--radius-md)">
        <table class="data-table" style="border: none">
          <thead>
            <tr><th>平台</th><th>比赛系列</th><th class="num-cell">难度基线 D（留空=默认）</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in difficultyFactors" :key="item.id">
              <td>{{ platformLabel(item.platform) }}</td>
              <td>{{ item.series }}</td>
              <td class="num-cell">
                <input
                  v-model="item.perf_base"
                  class="input"
                  type="number"
                  step="10"
                  min="200"
                  max="4000"
                  style="width: 140px"
                  placeholder="默认"
                  @blur="onBaseBlur(item)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="divider"></div>
      <button class="btn btn-primary" :disabled="saving" @click="onSave">
        {{ saving ? '保存中…' : '保存积分配置' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}
@media (max-width: 640px) {
  .grid-2 { grid-template-columns: 1fr; }
}
.divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-6) 0;
}
</style>
