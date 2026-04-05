<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { workflowStatus } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

const phase = ref('parsing')  // 'parsing' | 'analyzing' | 'done' | 'error'
const statusText = ref('正在解析 PDF 并分析题槽结构...')
const detail = ref('')
const percentage = ref(10)
const errorMsg = ref('')

let timer = null

onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先上传 PDF 文件')
    router.replace('/agent/upload')
    return
  }
  startPolling()
})

onUnmounted(() => {
  clearInterval(timer)
})

function startPolling() {
  statusText.value = '正在解析 PDF 并分析题槽结构...'
  percentage.value = 15

  timer = setInterval(async () => {
    try {
      const res = await workflowStatus(store.sessionId)
      const prog = res.progress || {}

      // 根据 parse/analyze 进度更新文字和进度条
      if (prog.parse_status === 'parsing') {
        phase.value = 'parsing'
        statusText.value = '正在调用视觉大模型解析 PDF 页面...'
        if (prog.parse_progress?.current != null && prog.parse_progress?.total != null) {
          detail.value = `已解析 ${prog.parse_progress.current} / ${prog.parse_progress.total} 页`
          percentage.value = Math.min(10 + Math.round((prog.parse_progress.current / prog.parse_progress.total) * 35), 45)
        }
      } else if (prog.analyze_status === 'analyzing') {
        phase.value = 'analyzing'
        statusText.value = '正在分析题槽结构与历年出题规律...'
        if (prog.analyze_progress?.slots_found != null) {
          detail.value = `已识别 ${prog.analyze_progress.slots_found} 个题槽`
          percentage.value = Math.min(45 + prog.analyze_progress.slots_found * 3, 80)
        } else {
          percentage.value = 50
        }
      }

      // 工作流中断（到了题槽确认点）
      if (res.status === 'interrupted') {
        clearInterval(timer)
        store.slotTemplate = res.slot_template || []
        store.analyzing = false
        percentage.value = 90
        phase.value = 'done'
        statusText.value = `题槽分析完成，共 ${store.slotTemplate.length} 个题槽`
        detail.value = '即将跳转到题槽确认页面...'
        setTimeout(() => router.push('/agent/slots'), 1200)
        return
      }

      // 工作流正常结束（无 interrupt，全部自动完成）
      if (res.status === 'done') {
        clearInterval(timer)
        store.slotTemplate = res.slot_template || []
        store.generatedQuestions = res.generated_questions || []
        phase.value = 'done'
        percentage.value = 100
        statusText.value = '处理完成'
        detail.value = '即将跳转到试卷草稿...'
        setTimeout(() => router.push('/agent/draft'), 1200)
        return
      }

      // 出错
      if (res.status === 'error') {
        clearInterval(timer)
        phase.value = 'error'
        errorMsg.value = res.error || prog.error || '工作流执行出错'
        percentage.value = 0
      }
    } catch {
      // http.js already shows error
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
      <div class="progress-card animate-fade-in-up">
        <!-- Header -->
        <div class="card-header">
          <div class="phase-icon" :class="`phase-icon--${phase}`">
            <svg v-if="phase === 'done'" width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="phase === 'error'" width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
              <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" class="spin-svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" stroke-dasharray="40 20" stroke-linecap="round"/>
            </svg>
          </div>

          <div class="card-titles">
            <h1 class="card-title">
              <span v-if="phase === 'parsing' || phase === 'analyzing'">解析往年题中</span>
              <span v-else-if="phase === 'done'">处理完成</span>
              <span v-else>处理失败</span>
            </h1>
            <p class="card-desc">{{ statusText }}</p>
          </div>
        </div>

        <!-- Progress Bar -->
        <div v-if="phase !== 'error'" class="progress-section">
          <div class="progress-track">
            <div
              class="progress-fill"
              :class="{ 'progress-fill--done': phase === 'done' }"
              :style="{ width: `${percentage}%` }"
            ></div>
          </div>
          <div class="progress-meta">
            <span class="progress-percent">{{ percentage }}%</span>
            <span class="progress-detail" v-if="detail">{{ detail }}</span>
          </div>
        </div>

        <!-- Error State -->
        <div v-else class="error-section">
          <div class="error-message">{{ errorMsg }}</div>
          <button class="retry-btn" @click="retry">重新上传</button>
        </div>

        <!-- Step Indicator -->
        <div class="steps">
          <div class="step" :class="{ active: phase === 'parsing', done: phase !== 'parsing' && phase !== 'error' }">
            <div class="step-dot"></div>
            <div class="step-label">PDF 解析</div>
          </div>
          <div class="step-connector" :class="{ done: phase === 'analyzing' || phase === 'done' }"></div>
          <div class="step" :class="{ active: phase === 'analyzing', done: phase === 'done' }">
            <div class="step-dot"></div>
            <div class="step-label">题槽分析</div>
          </div>
          <div class="step-connector" :class="{ done: phase === 'done' }"></div>
          <div class="step" :class="{ active: phase === 'done' }">
            <div class="step-dot"></div>
            <div class="step-label">确认生成</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: var(--color-bg);
}

.container.narrow {
  max-width: 540px;
  width: 100%;
}

/* ── Progress Card ────────────────────────────── */
.progress-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-10) var(--space-8);
}

/* ── Header ──────────────────────────────────── */
.card-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}

.phase-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phase-icon--parsing,
.phase-icon--analyzing {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.phase-icon--done {
  background: #E8F8EE;
  color: var(--color-success);
}

.phase-icon--error {
  background: #FFEBEA;
  color: var(--color-danger);
}

.spin-svg {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.card-titles {
  flex: 1;
}

.card-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.card-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* ── Progress ─────────────────────────────────── */
.progress-section {
  margin-bottom: var(--space-8);
}

.progress-track {
  height: 6px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-fill--done {
  background: var(--color-success);
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-2);
}

.progress-percent {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

.progress-detail {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* ── Error ──────────────────────────────────── */
.error-section {
  text-align: center;
  margin-bottom: var(--space-8);
}

.error-message {
  font-size: 14px;
  color: var(--color-danger);
  margin-bottom: var(--space-4);
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
  cursor: pointer;
  border: none;
  transition: background var(--transition-fast);
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}

/* ── Step Indicator ─────────────────────────── */
.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border);
  transition: all 0.3s;
}

.step.active .step-dot {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.step.done .step-dot {
  background: var(--color-success);
  border-color: var(--color-success);
}

.step-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.step.active .step-label {
  color: var(--color-primary);
}

.step.done .step-label {
  color: var(--color-success);
}

.step-connector {
  flex: 1;
  height: 2px;
  background: var(--color-border-light);
  margin: 0 var(--space-2);
  min-width: 40px;
  transition: background 0.3s;
}

.step-connector.done {
  background: var(--color-success);
}
</style>
