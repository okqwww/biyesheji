<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useAgentStore } from '../stores/agent'
import { startKg, getKg } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

// ── 状态 ─────────────────────────────────────────────
const phase = ref('idle')   // 'idle' | 'extracting' | 'done' | 'error'
const statusText = ref('')
const errorMsg = ref('')
let timer = null

// ── ECharts ──────────────────────────────────────────
const chartRef = ref(null)
let chart = null

// ── 数据 ─────────────────────────────────────────────
const nodes = computed(() => store.kgNodes)
const edges = computed(() => store.kgEdges)

const stats = computed(() => {
  const freqMax = Math.max(...nodes.value.map((n) => n.freq || 1), 1)
  const freqMin = Math.min(...nodes.value.map((n) => n.freq || 1), 1)
  return { total: nodes.value.length, edgeCount: edges.value.length, freqMax, freqMin }
})

// ── 生命周期 ─────────────────────────────────────────
onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先上传 PDF 并完成解析')
    router.replace('/agent/upload')
    return
  }

  // 如果已有数据，直接渲染
  if (store.kgStatus === 'done' && store.kgNodes.length > 0) {
    phase.value = 'done'
    statusText.value = `图谱就绪：${store.kgNodes.length} 个知识点`
    initChart()
    return
  }

  // 否则触发提取
  triggerExtract()
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})

// ── 提取流程 ─────────────────────────────────────────
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
      // http.js 已弹出错误
    }
  }, 3000)
}

function setError(msg) {
  phase.value = 'error'
  errorMsg.value = msg
}

// ── ECharts 渲染 ─────────────────────────────────────
function initChart() {
  // nextTick 后 DOM 才有
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

  const freqMax = stats.value.freqMax
  const freqMin = stats.value.freqMin
  const sizeRange = [18, 52]

  const ecNodes = nodes.value.map((n) => {
    const freq = n.freq || 1
    // 频次越高 → 节点越大、颜色越亮
    const ratio = freqMax === freqMin ? 0.5 : (freq - freqMin) / (freqMax - freqMin)
    const size = sizeRange[0] + ratio * (sizeRange[1] - sizeRange[0])

    // 高频：暖橙色；低频：冷蓝色
    const r = Math.round(99 + ratio * (251 - 99))
    const g = Math.round(102 + ratio * (146 - 102))
    const b = Math.round(241 + ratio * (0 - 241))
    const color = `rgb(${r},${g},${b})`

    return {
      id: n.id,
      name: n.id,
      value: freq,
      symbolSize: size,
      itemStyle: { color, borderColor: 'rgba(255,255,255,0.3)', borderWidth: 1 },
      label: {
        show: true,
        color: 'rgba(255,255,255,0.9)',
        fontSize: freq >= freqMax * 0.7 ? 13 : 11,
        fontWeight: freq >= freqMax * 0.7 ? 700 : 400,
      },
    }
  })

  const ecLinks = edges.value.map((e) => ({
    source: e.source,
    target: e.target,
    lineStyle: {
      color: e.relation === 'REQUIRES' ? 'rgba(248,113,113,0.5)' : 'rgba(129,140,248,0.4)',
      width: e.relation === 'REQUIRES' ? 2 : 1,
      type: e.relation === 'REQUIRES' ? 'solid' : 'dashed',
    },
  }))

  chart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (p) => {
          if (p.dataType === 'node') {
            return `<b>${p.data.name}</b><br/>出现频次：${p.data.value} 次`
          }
          const rel = edges.value.find(
            (e) => e.source === p.data.source && e.target === p.data.target,
          )
          const label = rel?.relation === 'REQUIRES' ? '依赖' : '相关'
          return `${p.data.source} <span style="opacity:.6">→ ${label} →</span> ${p.data.target}`
        },
      },
      legend: {
        data: ['相关 (RELATED_TO)', '依赖 (REQUIRES)'],
        orient: 'horizontal',
        bottom: 10,
        textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          data: ecNodes,
          links: ecLinks,
          force: {
            repulsion: 220,
            edgeLength: [80, 180],
            gravity: 0.08,
          },
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
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button text @click="$router.push('/agent/draft')">← 返回试卷草稿</el-button>
          <h1 class="page-title">课程知识图谱</h1>
          <el-tag v-if="phase === 'done'" type="success" effect="plain">
            {{ stats.total }} 个知识点 · {{ stats.edgeCount }} 条关联
          </el-tag>
        </div>
        <div class="toolbar-right">
          <span class="legend-item">
            <span class="legend-dot high"></span> 高频考点
          </span>
          <span class="legend-item">
            <span class="legend-dot low"></span> 低频考点
          </span>
          <span class="legend-item">
            <span class="legend-line dashed"></span> 相关
          </span>
          <span class="legend-item">
            <span class="legend-line solid red"></span> 依赖
          </span>
          <el-button
            v-if="phase === 'done'"
            size="small"
            @click="triggerExtract"
          >重新提取</el-button>
        </div>
      </div>

      <!-- 加载态 -->
      <div v-if="phase === 'extracting'" class="center-card glass">
        <div class="loading-spin"></div>
        <p class="loading-text">{{ statusText }}</p>
        <p class="loading-hint">DeepSeek 正在分析历年题目中的知识点及其关联关系，约需 15-30 秒...</p>
      </div>

      <!-- 空态（刚进入尚未触发） -->
      <div v-else-if="phase === 'idle'" class="center-card glass">
        <p class="loading-text">准备提取知识图谱...</p>
      </div>

      <!-- 错误态 -->
      <div v-else-if="phase === 'error'" class="center-card glass">
        <el-alert type="error" :title="errorMsg" show-icon :closable="false" />
        <el-button type="primary" class="mt16" @click="triggerExtract">重试</el-button>
      </div>

      <!-- 图谱渲染区 -->
      <div v-else class="graph-wrap glass">
        <div class="status-bar">
          <span class="status-text">{{ statusText }}</span>
          <span v-if="stats.freqMax > 1" class="freq-hint">
            最高频次：{{ stats.freqMax }} 次（节点越大、颜色越暖 = 考察越多）
          </span>
        </div>
        <div ref="chartRef" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.full-width {
  max-width: none;
  width: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
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
  flex-shrink: 0;
}

.legend-dot.high {
  background: rgb(251, 146, 0);
}

.legend-dot.low {
  background: rgb(99, 102, 241);
}

.legend-line {
  width: 22px;
  height: 2px;
  flex-shrink: 0;
}

.legend-line.dashed {
  background: repeating-linear-gradient(
    to right,
    rgba(129, 140, 248, 0.7) 0,
    rgba(129, 140, 248, 0.7) 4px,
    transparent 4px,
    transparent 8px
  );
}

.legend-line.solid {
  background: rgba(248, 113, 113, 0.7);
}

/* 加载/错误卡 */
.center-card {
  max-width: 560px;
  margin: 80px auto;
  padding: 48px 40px;
  border-radius: 20px;
  text-align: center;
}

.loading-spin {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(129, 140, 248, 0.2);
  border-top-color: #818cf8;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 10px;
}

.loading-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.mt16 {
  margin-top: 16px;
}

/* 图谱区 */
.graph-wrap {
  border-radius: 16px;
  overflow: hidden;
  padding: 0;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  flex-wrap: wrap;
  gap: 8px;
}

.status-text {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.freq-hint {
  color: rgba(255, 255, 255, 0.45);
}

.chart {
  height: calc(100vh - 200px);
  min-height: 500px;
  width: 100%;
}
</style>
