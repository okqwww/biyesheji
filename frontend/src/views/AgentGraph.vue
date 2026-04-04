<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useAgentStore } from '../stores/agent'
import { startKg, getKg } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

const phase = ref('idle')
const statusText = ref('')
const errorMsg = ref('')
let timer = null

const chartRef = ref(null)
let chart = null

const nodes = computed(() => store.kgNodes)
const edges = computed(() => store.kgEdges)

const stats = computed(() => ({
  total: nodes.value.length,
  edgeCount: edges.value.length,
}))

onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先上传 PDF 并完成解析')
    router.replace('/agent/upload')
    return
  }

  if (store.kgStatus === 'done' && store.kgNodes.length > 0) {
    phase.value = 'done'
    statusText.value = `图谱就绪：${store.kgNodes.length} 个知识点`
    initChart()
    return
  }

  triggerExtract()
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})

async function triggerExtract() {
  phase.value = 'extracting'
  statusText.value = '正在调用 AI 分析往年题，提取课程知识图谱...'
  store.extractingKg = true

  try {
    await startKg(store.sessionId)
  } catch {
    return
  }

  timer = setInterval(async () => {
    try {
      const res = await getKg(store.sessionId)
      if (res.status === 'done') {
        clearInterval(timer)
        store.kgStatus = 'done'
        store.kgNodes = res.kg_nodes || []
        store.kgEdges = res.kg_edges || []
        store.extractingKg = false
        phase.value = 'done'
        const prog = res.progress || {}
        statusText.value = `图谱提取完成：${prog.node_count ?? store.kgNodes.length} 个知识点，${prog.edge_count ?? store.kgEdges.length} 条关联`
        initChart()
      } else if (res.status === 'error') {
        clearInterval(timer)
        store.extractingKg = false
        setError((res.progress || {}).error || '知识图谱提取失败')
      }
    } catch {
      // http.js already shows error
    }
  }, 3000)
}

function setError(msg) {
  phase.value = 'error'
  errorMsg.value = msg
}

function initChart() {
  setTimeout(() => {
    if (!chartRef.value) return
    if (chart) {
      chart.dispose()
      chart = null
    }
    chart = echarts.init(chartRef.value)
    renderChart()
    window.addEventListener('resize', resizeChart)
  }, 100)
}

function resizeChart() {
  chart?.resize()
}

watch([nodes, edges], () => {
  if (phase.value === 'done') renderChart()
})

function renderChart() {
  if (!chart) return

  const freqMax = Math.max(...nodes.value.map((n) => n.freq || 1), 1)
  const freqMin = Math.min(...nodes.value.map((n) => n.freq || 1), 1)
  const sizeRange = [18, 52]

  const ecNodes = nodes.value.map((n) => {
    const freq = n.freq || 1
    const ratio = freqMax === freqMin ? 0.5 : (freq - freqMin) / (freqMax - freqMin)
    const size = sizeRange[0] + ratio * (sizeRange[1] - sizeRange[0])

    // Warm orange for high freq, cool blue for low freq
    const r = Math.round(99 + ratio * (251 - 99))
    const g = Math.round(102 + ratio * (146 - 102))
    const b = Math.round(241 + ratio * (0 - 241))
    const color = `rgb(${r},${g},${b})`

    return {
      id: n.id,
      name: n.id,
      value: freq,
      symbolSize: size,
      itemStyle: { color, borderColor: 'rgba(255,255,255,0.5)', borderWidth: 1 },
      label: {
        show: true,
        color: '#1D1D1F',
        fontSize: freq >= freqMax * 0.7 ? 13 : 11,
        fontWeight: freq >= freqMax * 0.7 ? 700 : 400,
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
    }
  })

  const ecLinks = edges.value.map((e) => ({
    source: e.source,
    target: e.target,
    lineStyle: {
      color: e.relation === 'REQUIRES' ? 'rgba(248, 113, 113, 0.6)' : 'rgba(99, 102, 241, 0.4)',
      width: e.relation === 'REQUIRES' ? 2 : 1,
      type: e.relation === 'REQUIRES' ? 'solid' : 'dashed',
    },
  }))

  chart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#ffffff',
        borderColor: '#D2D2D7',
        borderWidth: 1,
        borderRadius: 8,
        padding: [8, 12],
        textStyle: { color: '#1D1D1F', fontSize: 12, fontFamily: 'Inter, -apple-system, sans-serif' },
        formatter: (p) => {
          if (p.dataType === 'node') {
            return `<b>${p.data.name}</b><br/><span style="color:#86868B;font-size:11px">出现频次：${p.data.value} 次</span>`
          }
          const rel = edges.value.find((e) => e.source === p.data.source && e.target === p.data.target)
          const label = rel?.relation === 'REQUIRES' ? '依赖' : '相关'
          return `<span style="color:#86868B">${p.data.source} → ${label} → ${p.data.target}</span>`
        },
      },
      legend: {
        data: ['相关', '依赖'],
        orient: 'horizontal',
        bottom: 12,
        textStyle: { color: '#86868B', fontSize: 12, fontFamily: 'Inter, -apple-system, sans-serif' },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          data: ecNodes,
          links: ecLinks,
          force: { repulsion: 220, edgeLength: [80, 180], gravity: 0.08 },
          label: { position: 'right' },
          emphasis: { focus: 'adjacency', scale: 1.2 },
          lineStyle: { curveness: 0.1 },
        },
      ],
    },
    true,
  )
}
</script>

<template>
  <div class="page">
    <div class="container full-width">
      <!-- Toolbar -->
      <div class="toolbar animate-fade-in-up">
        <div class="toolbar-left">
          <button class="back-btn" @click="$router.push('/agent/draft')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <h1 class="page-title">课程知识图谱</h1>
          <span v-if="phase === 'done'" class="stat-badge">
            {{ stats.total }} 个知识点 · {{ stats.edgeCount }} 条关联
          </span>
        </div>

        <div class="toolbar-right">
          <span class="legend-item">
            <span class="legend-dot legend-dot--high"></span> 高频考点
          </span>
          <span class="legend-item">
            <span class="legend-dot legend-dot--low"></span> 低频考点
          </span>
          <span class="legend-item">
            <span class="legend-line legend-line--dashed"></span> 相关
          </span>
          <span class="legend-item">
            <span class="legend-line legend-line--solid"></span> 依赖
          </span>
          <button v-if="phase === 'done'" class="re-extract-btn" @click="triggerExtract">
            重新提取
          </button>
        </div>
      </div>

      <!-- Extracting State -->
      <div v-if="phase === 'extracting'" class="center-card animate-fade-in">
        <div class="loading-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" class="spin-svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" stroke-dasharray="40 20" stroke-linecap="round"/>
          </svg>
        </div>
        <p class="loading-text">{{ statusText }}</p>
        <p class="loading-hint">DeepSeek 正在分析历年题目中的知识点及其关联关系，约需 15-30 秒...</p>
      </div>

      <!-- Idle State -->
      <div v-else-if="phase === 'idle'" class="center-card animate-fade-in">
        <p class="loading-text">准备提取知识图谱...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="phase === 'error'" class="center-card animate-fade-in">
        <div class="error-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
            <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <p class="error-text">{{ errorMsg }}</p>
        <button class="retry-btn" @click="triggerExtract">重试</button>
      </div>

      <!-- Graph Area -->
      <div v-else class="graph-wrap animate-fade-in">
        <div class="graph-header">
          <span class="graph-status">{{ statusText }}</span>
        </div>
        <div ref="chartRef" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-top: var(--space-8);
  background: var(--color-bg);
}

.full-width {
  max-width: none;
  width: 100%;
}

/* ── Toolbar ─────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.back-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.page-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: #E8F8EE;
  color: var(--color-success);
  font-size: 12px;
  font-weight: 500;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font-size: 12px;
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot--high {
  background: rgb(251, 146, 60);
}

.legend-dot--low {
  background: rgb(99, 102, 241);
}

.legend-line {
  width: 22px;
  height: 2px;
}

.legend-line--dashed {
  background: repeating-linear-gradient(
    to right,
    rgba(99, 102, 241, 0.7) 0,
    rgba(99, 102, 241, 0.7) 4px,
    transparent 4px,
    transparent 8px
  );
}

.legend-line--solid {
  background: rgba(248, 113, 113, 0.7);
}

.re-extract-btn {
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border: 1px solid rgba(0, 122, 255, 0.2);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.re-extract-btn:hover {
  background: #D4EBFF;
}

/* ── Center Card ─────────────────────────────── */
.center-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-12) var(--space-8);
  text-align: center;
  max-width: 480px;
  margin: var(--space-16) auto;
}

.loading-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius);
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-5);
}

.spin-svg {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.loading-hint {
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.error-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius);
  background: #FFEBEA;
  color: var(--color-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-5);
}

.error-text {
  font-size: 14px;
  color: var(--color-danger);
  margin-bottom: var(--space-5);
}

.retry-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 20px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  background: var(--color-primary);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}

/* ── Graph Area ─────────────────────────────── */
.graph-wrap {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.graph-header {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.graph-status {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.chart {
  height: calc(100vh - 200px);
  min-height: 500px;
  width: 100%;
}
</style>
