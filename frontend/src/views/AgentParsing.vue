<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { getParsed, startAnalyze, getAnalyzed } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

// ── 状态 ─────────────────────────────────────────────
const phase = ref('parsing')  // 'parsing' | 'analyzing' | 'done' | 'error'
const statusText = ref('正在调用视觉大模型解析 PDF 页面...')
const detail = ref('')
const percentage = ref(10)
const errorMsg = ref('')

let timer = null

// ── 卫兵：没有 sessionId 就打回首页 ───────────────────
onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先上传 PDF 文件')
    router.replace('/agent/upload')
    return
  }
  startPollingParse()
})

onUnmounted(() => {
  clearInterval(timer)
})

// ── 阶段一：轮询解析 ──────────────────────────────────
function startPollingParse() {
  phase.value = 'parsing'
  statusText.value = '正在调用视觉大模型解析 PDF 页面...'
  percentage.value = 15

  timer = setInterval(async () => {
    try {
      const res = await getParsed(store.sessionId)
      const prog = res.progress || {}

      if (prog.current != null && prog.total != null) {
        detail.value = `已解析 ${prog.current} / ${prog.total} 页`
        percentage.value = Math.min(10 + Math.round((prog.current / prog.total) * 45), 55)
      }

      if (res.status === 'done') {
        clearInterval(timer)
        store.parsedExams = res.parsed_exams || []
        percentage.value = 55
        detail.value = `解析完成，共 ${store.parsedExams.length} 份试卷`
        await triggerAnalyze()
      } else if (res.status === 'error') {
        clearInterval(timer)
        setError(prog.error || '解析失败')
      }
    } catch {
      // http.js 已弹出错误
    }
  }, 3000)
}

// ── 阶段二：启动分析后轮询 ────────────────────────────
async function triggerAnalyze() {
  try {
    await startAnalyze(store.sessionId)
  } catch {
    return
  }

  phase.value = 'analyzing'
  statusText.value = '正在分析题槽结构与历年出题规律...'
  percentage.value = 60

  timer = setInterval(async () => {
    try {
      const res = await getAnalyzed(store.sessionId)
      const prog = res.progress || {}

      if (prog.slots_found != null) {
        detail.value = `已识别 ${prog.slots_found} 个题槽`
        percentage.value = Math.min(60 + prog.slots_found * 2, 90)
      }

      if (res.status === 'done') {
        clearInterval(timer)
        store.slotTemplate = res.slot_template || []
        store.analyzing = false
        percentage.value = 100
        phase.value = 'done'
        statusText.value = `分析完成，共识别 ${store.slotTemplate.length} 个题槽`
        detail.value = '即将跳转到题槽确认页面...'
        setTimeout(() => router.push('/agent/slots'), 1200)
      } else if (res.status === 'error') {
        clearInterval(timer)
        setError(prog.error || '题槽分析失败')
      }
    } catch {
      // http.js 已弹出错误
    }
  }, 3000)
}

function setError(msg) {
  phase.value = 'error'
  errorMsg.value = msg
  percentage.value = 0
}

function retry() {
  router.replace('/agent/upload')
}
</script>

<template>
  <div class="page">
    <div class="container narrow">
      <div class="card glass">
        <!-- 标题区 -->
        <div class="card-header">
          <h1 class="card-title">
            <span v-if="phase === 'parsing'">解析往年题中</span>
            <span v-else-if="phase === 'analyzing'">分析题槽结构中</span>
            <span v-else-if="phase === 'done'">处理完成 ✓</span>
            <span v-else>处理失败</span>
          </h1>
          <p class="card-desc">{{ statusText }}</p>
        </div>

        <!-- 进度条 -->
        <div v-if="phase !== 'error'" class="progress-wrap">
          <el-progress
            :percentage="percentage"
            :status="phase === 'done' ? 'success' : undefined"
            :stroke-width="10"
            :duration="600"
            striped
            :striped-flow="phase !== 'done'"
          />
          <div class="detail-text" v-if="detail">{{ detail }}</div>
        </div>

        <!-- 错误态 -->
        <div v-else class="error-block">
          <el-alert type="error" :title="errorMsg" show-icon :closable="false" />
          <el-button type="primary" class="retry-btn" @click="retry">重新上传</el-button>
        </div>

        <!-- 步骤指示器 -->
        <div class="steps">
          <div class="step" :class="{ active: phase === 'parsing', done: phase !== 'parsing' && phase !== 'error' }">
            <div class="step-dot"></div>
            <div class="step-label">Agent 1<br />PDF 解析</div>
          </div>
          <div class="step-line" :class="{ done: phase === 'analyzing' || phase === 'done' }"></div>
          <div class="step" :class="{ active: phase === 'analyzing', done: phase === 'done' }">
            <div class="step-dot"></div>
            <div class="step-label">Agent 2<br />题槽分析</div>
          </div>
          <div class="step-line"></div>
          <div class="step" :class="{ active: phase === 'done' }">
            <div class="step-dot"></div>
            <div class="step-label">确认题槽<br />开始生题</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 640px;
}

.card {
  padding: 40px 36px;
  border-radius: 20px;
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.card-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
}

.card-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0;
}

.progress-wrap {
  margin-bottom: 36px;
}

.detail-text {
  margin-top: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  text-align: center;
}

.error-block {
  margin-bottom: 24px;
  text-align: center;
}

.retry-btn {
  margin-top: 16px;
}

/* 步骤指示器 */
.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding-top: 8px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.step-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s;
}

.step.active .step-dot {
  background: #818cf8;
  border-color: #818cf8;
  box-shadow: 0 0 10px rgba(129, 140, 248, 0.6);
}

.step.done .step-dot {
  background: #34d399;
  border-color: #34d399;
}

.step-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  line-height: 1.5;
}

.step.active .step-label,
.step.done .step-label {
  color: rgba(255, 255, 255, 0.85);
}

.step-line {
  flex: 1;
  height: 2px;
  background: rgba(255, 255, 255, 0.15);
  margin: 0 6px;
  margin-bottom: 24px;
  transition: background 0.3s;
}

.step-line.done {
  background: #34d399;
}
</style>
