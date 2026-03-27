<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { getGenerated, regenerate } from '../api/agent'
import LatexRenderer from '../components/LatexRenderer.vue'

const router = useRouter()
const store = useAgentStore()

// ── 轮询状态 ──────────────────────────────────────────
const loading = ref(true)
const percentage = ref(10)
const statusText = ref('正在并行生成各题槽的题目...')
let timer = null

// ── 每道题的 UI 状态 ──────────────────────────────────
// { [slotId]: { expanded: bool, showAnswer: bool, satisfied: bool|null, feedback: string, regenerating: bool } }
const cardState = ref({})

// ── 展示的题目列表 ─────────────────────────────────────
const questions = ref([])

onMounted(() => {
  if (!store.sessionId) {
    ElMessage.warning('请先完成上传与分析')
    router.replace('/agent/upload')
    return
  }
  // 如果已有结果（从题槽页返回再进入）直接展示
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
      // http.js 已弹出错误
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
    cardState.value[slotId] = {
      expanded: false,
      showAnswer: false,
      satisfied: null,
      feedback: '',
      regenerating: false,
    }
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
    // 替换本地列表
    const idx = questions.value.findIndex((x) => x.slot_id === q.slot_id)
    if (idx !== -1) questions.value.splice(idx, 1, newQ)
    store.replaceQuestion(q.slot_id, newQ)
    s.satisfied = null
    s.feedback = ''
    s.expanded = false
    ElMessage.success('题目已重新生成')
  } catch {
    // http.js 已弹出错误
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
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button text @click="$router.push('/agent/slots')">← 返回题槽页</el-button>
          <h1 class="page-title">试卷草稿</h1>
          <el-tag v-if="!loading" type="success" effect="plain">
            共 {{ questions.length }} 道题 · 改动幅度：{{ levelLabel(store.modificationLevel) }}
          </el-tag>
        </div>
        <el-button v-if="!loading && questions.length" type="default" @click="copyAll">
          复制全卷文本
        </el-button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-card glass">
        <h2 class="loading-title">Agent 4 正在并行出题中</h2>
        <p class="loading-desc">{{ statusText }}</p>
        <el-progress
          :percentage="percentage"
          :stroke-width="10"
          striped
          striped-flow
          class="loading-progress"
        />
        <p class="loading-hint">每道题独立调用 LLM，多题并行生成，请耐心等候...</p>
      </div>

      <!-- 题目列表 -->
      <div v-else class="questions-list">
        <div
          v-for="(q, idx) in questions"
          :key="q.slot_id"
          class="q-card glass"
        >
          <!-- 卡片头部 -->
          <div class="q-head">
            <div class="q-num">{{ idx + 1 }}</div>
            <div class="q-info">
              <span class="q-type">{{ q.type }}</span>
              <span class="q-points">{{ q.points }} 分</span>
            </div>
            <div class="q-actions-head">
              <el-tag
                v-if="getState(q.slot_id).satisfied === true"
                type="success"
                size="small"
                effect="plain"
              >已确认</el-tag>
              <el-tag
                v-else-if="getState(q.slot_id).satisfied === false"
                type="warning"
                size="small"
                effect="plain"
              >待修改</el-tag>
            </div>
          </div>

          <!-- 题目内容 -->
          <div class="q-content">
            <LatexRenderer :content="q.content" />
          </div>

          <!-- 答案折叠 -->
          <div class="q-answer-wrap">
            <el-button
              text
              size="small"
              class="toggle-answer"
              @click="getState(q.slot_id).showAnswer = !getState(q.slot_id).showAnswer"
            >
              {{ getState(q.slot_id).showAnswer ? '收起答案 ▲' : '查看参考答案 ▼' }}
            </el-button>
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

          <!-- 满意 / 不满意操作 -->
          <div class="q-footer">
            <div class="q-satisfaction">
              <el-button
                size="small"
                :type="getState(q.slot_id).satisfied === true ? 'success' : 'default'"
                @click="getState(q.slot_id).satisfied = true; getState(q.slot_id).expanded = false"
              >
                ✓ 满意
              </el-button>
              <el-button
                size="small"
                :type="getState(q.slot_id).satisfied === false ? 'warning' : 'default'"
                @click="getState(q.slot_id).satisfied = false; getState(q.slot_id).expanded = true"
              >
                ✗ 不满意
              </el-button>
            </div>
          </div>

          <!-- 反馈输入区（不满意时展开） -->
          <div v-if="getState(q.slot_id).expanded" class="q-feedback">
            <div class="feedback-label">请描述您的修改意见，AI 将据此重新生成这道题：</div>
            <el-input
              v-model="getState(q.slot_id).feedback"
              type="textarea"
              :rows="3"
              placeholder="例如：请把计算题改成证明题；难度太低，请加大难度；公式太少，多加一些推导步骤..."
              class="feedback-input"
            />
            <div class="feedback-actions">
              <el-button
                type="primary"
                size="small"
                :loading="getState(q.slot_id).regenerating"
                @click="doRegenerate(q)"
              >
                {{ getState(q.slot_id).regenerating ? '重新生成中...' : '重新生成这道题' }}
              </el-button>
              <el-button
                text
                size="small"
                @click="getState(q.slot_id).expanded = false; getState(q.slot_id).satisfied = null"
              >取消</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}

/* 加载卡片 */
.loading-card {
  padding: 48px 40px;
  border-radius: 20px;
  text-align: center;
  max-width: 600px;
  margin: 0 auto;
}

.loading-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 10px;
}

.loading-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0 0 24px;
}

.loading-progress {
  margin-bottom: 16px;
}

.loading-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

/* 题目列表 */
.questions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 40px;
}

.q-card {
  border-radius: 14px;
  padding: 20px 24px;
}

.q-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.q-num {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(129, 140, 248, 0.2);
  color: #818cf8;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.q-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.q-type {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}

.q-points {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.q-actions-head {
  flex-shrink: 0;
}

/* 题目内容 */
.q-content {
  font-size: 15px;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

/* 答案区 */
.q-answer-wrap {
  margin-bottom: 10px;
}

.toggle-answer {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
  padding: 0;
}

.q-answer {
  margin-top: 10px;
  padding: 14px 16px;
  background: rgba(52, 211, 153, 0.06);
  border: 1px solid rgba(52, 211, 153, 0.15);
  border-radius: 8px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.answer-label {
  font-size: 12px;
  font-weight: 600;
  color: #34d399;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

.scoring-section {
  margin-top: 14px;
}

.scoring-list {
  margin: 4px 0 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.7);
}

/* 底部操作 */
.q-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.q-satisfaction {
  display: flex;
  gap: 8px;
}

/* 反馈区 */
.q-feedback {
  margin-top: 14px;
  padding: 16px;
  background: rgba(245, 158, 11, 0.07);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 8px;
}

.feedback-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 10px;
}

.feedback-input {
  margin-bottom: 12px;
}

.feedback-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
