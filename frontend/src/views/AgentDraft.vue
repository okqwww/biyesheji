<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { getGenerated, regenerate } from '../api/agent'
import LatexRenderer from '../components/LatexRenderer.vue'

const router = useRouter()
const store = useAgentStore()

const loading = ref(true)
const percentage = ref(10)
const statusText = ref('正在并行生成各题槽的题目...')
let timer = null

const cardState = ref({})
const questions = ref([])

onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先完成上传与分析')
    router.replace('/agent/upload')
    return
  }
  if (store.generatedQuestions.length > 0) {
    questions.value = [...store.generatedQuestions]
    initCardStates()
    loading.value = false
    return
  }
  startPolling()
})

onUnmounted(() => {
  clearInterval(timer)
})

function startPolling() {
  loading.value = true
  percentage.value = 10

  timer = setInterval(async () => {
    try {
      const res = await getGenerated(store.sessionId)
      const prog = res.progress || {}

      if (prog.done != null && prog.total != null) {
        percentage.value = Math.min(10 + Math.round((prog.done / prog.total) * 88), 98)
        statusText.value = `已生成 ${prog.done} / ${prog.total} 道题...`
      }

      if (res.status === 'done') {
        clearInterval(timer)
        store.generatedQuestions = res.generated_questions || []
        questions.value = [...store.generatedQuestions]
        initCardStates()
        percentage.value = 100
        loading.value = false
        store.generating = false
      } else if (res.status === 'error') {
        clearInterval(timer)
        loading.value = false
        ElMessage.error(prog.error || '题目生成失败')
      }
    } catch {
      // http.js already shows error
    }
  }, 3000)
}

function initCardStates() {
  for (const q of questions.value) {
    if (!cardState.value[q.slot_id]) {
      cardState.value[q.slot_id] = {
        expanded: false,
        showAnswer: false,
        satisfied: null,
        feedback: '',
        regenerating: false,
      }
    }
  }
}

function getState(slotId) {
  if (!cardState.value[slotId]) {
    cardState.value[slotId] = { expanded: false, showAnswer: false, satisfied: null, feedback: '', regenerating: false }
  }
  return cardState.value[slotId]
}

async function doRegenerate(q) {
  const s = getState(q.slot_id)
  if (!s.feedback.trim()) {
    ElMessage.warning('请先输入对该题目的修改意见')
    return
  }
  s.regenerating = true
  try {
    const res = await regenerate(store.sessionId, q.slot_id, s.feedback)
    const newQ = res.question
    const idx = questions.value.findIndex((x) => x.slot_id === q.slot_id)
    if (idx !== -1) questions.value.splice(idx, 1, newQ)
    store.replaceQuestion(q.slot_id, newQ)
    s.satisfied = null
    s.feedback = ''
    s.expanded = false
    ElMessage.success('题目已重新生成')
  } catch {
    // http.js already shows error
  } finally {
    s.regenerating = false
  }
}

function levelLabel(level) {
  return { small: '小改', medium: '中改', large: '大改' }[level] || level
}

function copyAll() {
  const lines = questions.value.map((q, i) => {
    return [
      `第 ${i + 1} 题（${q.type} · ${q.points} 分）`,
      q.content,
      '',
      '【参考答案】',
      q.answer,
      q.scoring_criteria?.length
        ? '\n【评分标准】\n' + q.scoring_criteria.map((s, j) => `${j + 1}. ${s}`).join('\n')
        : '',
    ].join('\n')
  })
  navigator.clipboard
    .writeText(lines.join('\n\n' + '─'.repeat(40) + '\n\n'))
    .then(() => ElMessage.success('已复制全卷到剪贴板'))
    .catch(() => ElMessage.error('复制失败，请手动选择文本'))
}
</script>

<template>
  <div class="page">
    <div class="container">
      <!-- Toolbar -->
      <div class="toolbar animate-fade-in-up">
        <div class="toolbar-left">
          <button class="back-btn" @click="$router.push('/agent/slots')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <div>
            <h1 class="page-title">试卷草稿</h1>
            <p class="page-subtitle" v-if="!loading">
              共 {{ questions.length }} 道题 · {{ levelLabel(store.modificationLevel) }}
            </p>
          </div>
        </div>

        <div v-if="!loading && questions.length" class="toolbar-actions">
          <button class="action-btn" @click="$router.push('/agent/graph')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="4" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="20" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="4" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="20" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            查看知识图谱
          </button>
          <button class="action-btn" @click="copyAll">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <path d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            复制全卷
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-card animate-fade-in-up">
        <div class="loading-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" class="spin-svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" stroke-dasharray="40 20" stroke-linecap="round"/>
          </svg>
        </div>
        <h2 class="loading-title">Agent 4 正在并行出题中</h2>
        <p class="loading-desc">{{ statusText }}</p>

        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${percentage}%` }"></div>
        </div>
        <div class="progress-meta">
          <span class="progress-pct">{{ percentage }}%</span>
        </div>

        <p class="loading-hint">每道题独立调用 LLM，多题并行生成，请耐心等候...</p>
      </div>

      <!-- Question List -->
      <div v-else class="questions-list">
        <div
          v-for="(q, idx) in questions"
          :key="q.slot_id"
          class="q-card animate-fade-in-up"
          :style="{ animationDelay: `${idx * 50}ms` }"
        >
          <!-- Card Header -->
          <div class="q-header">
            <div class="q-num">{{ idx + 1 }}</div>
            <div class="q-meta">
              <span class="q-type">{{ q.type }}</span>
              <span class="q-points">{{ q.points }} 分</span>
            </div>
            <div class="q-status">
              <span
                v-if="getState(q.slot_id).satisfied === true"
                class="status-badge status-badge--success"
              >已确认</span>
              <span
                v-else-if="getState(q.slot_id).satisfied === false"
                class="status-badge status-badge--warning"
              >待修改</span>
            </div>
          </div>

          <!-- Question Content -->
          <div class="q-body">
            <LatexRenderer :content="q.content" />
          </div>

          <!-- Answer Toggle -->
          <div class="q-answer-toggle">
            <button
              class="toggle-btn"
              @click="getState(q.slot_id).showAnswer = !getState(q.slot_id).showAnswer"
            >
              {{ getState(q.slot_id).showAnswer ? '收起答案' : '查看参考答案' }}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" :style="{ transform: getState(q.slot_id).showAnswer ? 'rotate(180deg)' : 'none' }">
                <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>

            <div v-if="getState(q.slot_id).showAnswer" class="q-answer">
              <div class="answer-label">参考答案</div>
              <LatexRenderer :content="q.answer" />
              <div v-if="q.scoring_criteria?.length" class="scoring-section">
                <div class="answer-label">评分标准</div>
                <ol class="scoring-list">
                  <li v-for="(sc, si) in q.scoring_criteria" :key="si">
                    <LatexRenderer :content="sc" />
                  </li>
                </ol>
              </div>
            </div>
          </div>

          <!-- Satisfaction Buttons -->
          <div class="q-footer">
            <div class="satisfaction-btns">
              <button
                class="sat-btn"
                :class="{ 'sat-btn--success': getState(q.slot_id).satisfied === true }"
                @click="getState(q.slot_id).satisfied = true; getState(q.slot_id).expanded = false"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                满意
              </button>
              <button
                class="sat-btn"
                :class="{ 'sat-btn--warning': getState(q.slot_id).satisfied === false }"
                @click="getState(q.slot_id).satisfied = false; getState(q.slot_id).expanded = true"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                不满意
              </button>
            </div>
          </div>

          <!-- Feedback Area -->
          <div v-if="getState(q.slot_id).expanded" class="feedback-area">
            <div class="feedback-label">请描述您的修改意见，AI 将据此重新生成：</div>
            <el-input
              v-model="getState(q.slot_id).feedback"
              type="textarea"
              :rows="3"
              placeholder="例如：请把计算题改成证明题；难度太低，请加大难度..."
              class="feedback-input"
            />
            <div class="feedback-actions">
              <button
                class="regen-btn"
                :disabled="getState(q.slot_id).regenerating"
                @click="doRegenerate(q)"
              >
                <span v-if="getState(q.slot_id).regenerating" class="spinner"></span>
                {{ getState(q.slot_id).regenerating ? '重新生成中...' : '重新生成这道题' }}
              </button>
              <button
                class="cancel-btn"
                @click="getState(q.slot_id).expanded = false; getState(q.slot_id).satisfied = null"
              >取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-top: var(--space-10);
  background: var(--color-bg);
}

/* ── Toolbar ─────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
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
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: 2px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.toolbar-actions {
  display: flex;
  gap: var(--space-2);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

/* ── Loading Card ─────────────────────────────── */
.loading-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-10) var(--space-8);
  text-align: center;
  max-width: 520px;
  margin: 0 auto;
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

.loading-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.loading-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-6);
}

.progress-track {
  height: 6px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-2);
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-meta {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-4);
}

.progress-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
}

.loading-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

/* ── Question List ─────────────────────────────── */
.questions-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-bottom: var(--space-12);
}

/* ── Question Card ─────────────────────────────── */
.q-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: box-shadow var(--transition-base);
}

.q-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.q-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
}

.q-num {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.q-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.q-type {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.q-points {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
}

.status-badge--success {
  background: #E8F8EE;
  color: var(--color-success);
}

.status-badge--warning {
  background: #FFF4E5;
  color: var(--color-warning);
}

/* ── Question Body ─────────────────────────────── */
.q-body {
  padding: var(--space-5);
  font-size: 15px;
  line-height: 1.75;
  color: var(--color-text);
  background: var(--color-bg);
}

/* ── Answer Toggle ─────────────────────────────── */
.q-answer-toggle {
  padding: 0 var(--space-5);
}

.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  background: none;
  border: none;
  padding: var(--space-2) 0;
  transition: color var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--color-primary);
}

.q-answer {
  padding: var(--space-4);
  background: #F0F9EB;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(52, 199, 89, 0.2);
  margin-bottom: var(--space-4);
}

.answer-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-success);
  margin-bottom: var(--space-2);
}

.scoring-section {
  margin-top: var(--space-3);
}

.scoring-list {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-5);
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.9;
}

/* ── Footer / Satisfaction ─────────────────────── */
.q-footer {
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.satisfaction-btns {
  display: flex;
  gap: var(--space-2);
}

.sat-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sat-btn:hover {
  border-color: var(--color-border);
}

.sat-btn--success {
  background: #E8F8EE;
  color: var(--color-success);
  border-color: rgba(52, 199, 89, 0.3);
}

.sat-btn--warning {
  background: #FFF4E5;
  color: var(--color-warning);
  border-color: rgba(255, 149, 0, 0.3);
}

/* ── Feedback Area ─────────────────────────────── */
.feedback-area {
  padding: var(--space-4) var(--space-5);
  background: #FFFBEA;
  border-top: 1px solid rgba(255, 149, 0, 0.15);
}

.feedback-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
}

.feedback-input {
  margin-bottom: var(--space-3);
}

.feedback-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.regen-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  background: var(--color-primary);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.regen-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.regen-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px 12px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
