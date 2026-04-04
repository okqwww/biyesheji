<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useCourseStore } from '../stores/course'
import { useQuestionStore } from '../stores/question'
import { exportMarkdown, saveQuestions } from '../api/questions'

const router = useRouter()
const courseStore = useCourseStore()
const questionStore = useQuestionStore()

const questions = computed(() => questionStore.generatedQuestions || [])
const courseName = computed(() => courseStore.currentCourse?.name || questionStore.courseId || '')

const saving = ref(false)
const saved = ref(false)

function isShortAnswer(question) {
  return question.type === 'short_answer' || question.type === '解答题'
}

function hasCodeBlock(text) {
  if (!text) return false
  const lines = text.split('\n')
  return lines.length > 2 && lines.some(line => line.startsWith('    ') || line.startsWith('\t'))
}

function goBack() {
  router.back()
}

async function regenerate() {
  if (!questionStore.lastGeneratePayload) {
    router.push('/courses')
    return
  }

  try {
    await ElMessageBox.confirm('确认重新生成题目？当前页面展示的结果将会被覆盖。', '重新生成', {
      confirmButtonText: '重新生成',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  saved.value = false
  await questionStore.generate(questionStore.lastGeneratePayload)
}

async function exportQuestions() {
  if (!questions.value || questions.value.length === 0) {
    ElMessage.warning('暂无题目可导出')
    return
  }

  try {
    ElMessage.info('正在生成导出文件...')
    const markdown = await exportMarkdown(questions.value)
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const filename = `题目_${courseName.value || '未知课程'}_${date}.md`
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功！')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败，请重试')
  }
}

async function saveQuestionsToDb() {
  if (!questions.value || questions.value.length === 0) {
    ElMessage.warning('暂无题目可保存')
    return
  }

  if (!questionStore.selectedKnowledgePointIds || questionStore.selectedKnowledgePointIds.length === 0) {
    ElMessage.warning('缺少知识点信息，无法保存')
    return
  }

  if (saved.value) {
    try {
      await ElMessageBox.confirm('题目已保存过，是否重复保存？', '提示', {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
  }

  saving.value = true
  try {
    const payload = {
      questions: questions.value,
      knowledge_point_ids: questionStore.selectedKnowledgePointIds
    }
    const result = await saveQuestions(payload)
    if (result.success) {
      saved.value = true
      ElMessage.success(result.message || `成功保存 ${questions.value.length} 道题目`)
    } else {
      ElMessage.error(result.message || '保存失败')
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const typeTagClass = (type) => {
  if (type?.includes('选择')) return 'tag--primary'
  if (type?.includes('判断')) return 'tag--success'
  if (type?.includes('填空')) return 'tag--warning'
  if (type?.includes('问答') || type?.includes('简答') || type?.includes('解答')) return 'tag--danger'
  return ''
}

const difficultyTagClass = (d) => {
  if (d === 'easy' || d === '简单') return 'tag--success'
  if (d === 'hard' || d === '困难') return 'tag--danger'
  return 'tag--warning'
}
</script>

<template>
  <div class="page">
    <div class="container">
      <!-- Header -->
      <div class="page-header animate-fade-in-up">
        <div class="header-left">
          <button class="back-btn" @click="goBack">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <div>
            <h1 class="page-title">题目结果</h1>
            <p class="page-subtitle">{{ courseName }} · 共 {{ questions.length }} 题</p>
          </div>
        </div>

        <div class="header-actions">
          <button class="action-btn" @click="goBack">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <button class="action-btn" @click="exportQuestions">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="7,10 12,15 17,10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <line x1="12" y1="15" x2="12" y2="3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            导出
          </button>
          <button class="action-btn" :class="{ 'action-btn--success': saved }" :loading="saving" @click="saveQuestionsToDb">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H16L21 8V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="17,21 17,13 7,13 7,21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="7,3 7,8 15,8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ saved ? '已保存' : '保存' }}
          </button>
          <button class="action-btn action-btn--primary" :loading="questionStore.generating" @click="regenerate">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <polyline points="23,4 23,10 17,10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            重新生成
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <el-empty v-if="questions.length === 0" description="暂无题目数据，请返回重新生成" />

      <!-- Question List -->
      <div v-else class="question-list">
        <div
          v-for="(q, idx) in questions"
          :key="idx"
          class="q-card animate-fade-in-up"
          :style="{ animationDelay: `${idx * 60}ms` }"
        >
          <!-- Card Header -->
          <div class="q-card__header">
            <div class="q-number">第 {{ idx + 1 }} 题</div>
            <div class="q-tags">
              <span class="tag" :class="typeTagClass(q.type)">{{ q.type }}</span>
              <span class="tag" :class="difficultyTagClass(q.difficulty)">{{ q.difficulty }}</span>
            </div>
          </div>

          <!-- Question Content -->
          <div class="q-section">
            <div class="q-label">题目</div>
            <div class="q-content">{{ q.content }}</div>
          </div>

          <!-- Knowledge Points -->
          <div class="q-section" v-if="q.knowledge_points && q.knowledge_points.length">
            <div class="q-label">考察知识点</div>
            <div class="kp-list">
              <span v-for="(kp, kIdx) in q.knowledge_points" :key="kIdx" class="kp-chip">{{ kp }}</span>
            </div>
          </div>

          <!-- Options -->
          <div class="q-section" v-if="q.options && q.options.length">
            <div class="q-label">选项</div>
            <div class="options">
              <div v-for="(op, oIdx) in q.options" :key="oIdx" class="option-item">{{ op }}</div>
            </div>
          </div>

          <!-- Answer -->
          <div class="q-section">
            <div class="q-label">参考答案</div>
            <div v-if="isShortAnswer(q) && hasCodeBlock(q.answer)" class="answer-code">
              <pre><code>{{ q.answer }}</code></pre>
            </div>
            <div v-else class="answer-text">
              <span v-if="Array.isArray(q.answer)">{{ q.answer.join(', ') }}</span>
              <span v-else>{{ q.answer }}</span>
            </div>
          </div>

          <!-- Explanation -->
          <div class="q-section" v-if="q.explanation">
            <div class="q-label">解析</div>
            <div class="q-text">{{ q.explanation }}</div>
          </div>

          <!-- Scoring Points -->
          <div class="q-section" v-if="q.scoring_points && q.scoring_points.length">
            <div class="q-label">评分点</div>
            <div class="score-list">
              <div v-for="(sp, sIdx) in q.scoring_points" :key="sIdx" class="score-item">
                <span class="score-bullet"></span>
                {{ sp }}
              </div>
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

/* ── Page Header ────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
  flex-wrap: wrap;
}

.header-left {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* ── Action Buttons ──────────────────────────── */
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
  border-color: var(--color-border);
}

.action-btn--success {
  color: var(--color-success);
  border-color: rgba(52, 199, 89, 0.3);
  background: #E8F8EE;
}

.action-btn--primary {
  background: var(--color-primary);
  color: #ffffff;
  border-color: var(--color-primary);
}

.action-btn--primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  color: #ffffff;
}

/* ── Question List ───────────────────────────── */
.question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-bottom: var(--space-12);
}

/* ── Question Card ───────────────────────────── */
.q-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-6);
  transition: box-shadow var(--transition-base);
}

.q-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.q-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.q-number {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
}

.q-tags {
  display: flex;
  gap: var(--space-2);
}

/* ── Question Sections ───────────────────────── */
.q-section {
  margin-bottom: var(--space-4);
}

.q-section:last-child {
  margin-bottom: 0;
}

.q-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
}

.q-content {
  font-size: 15px;
  line-height: 1.75;
  color: var(--color-text);
  white-space: pre-wrap;
}

.q-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
}

/* ── Knowledge Points ─────────────────────────── */
.kp-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kp-chip {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
}

/* ── Options ────────────────────────────────── */
.options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.option-item {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.5;
}

/* ── Answer ──────────────────────────────────── */
.answer-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.answer-code {
  margin-top: var(--space-2);
}

.answer-code pre {
  margin: 0;
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  background: #1D1D1F;
  overflow-x: auto;
}

.answer-code code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #E8EAED;
  white-space: pre;
  display: block;
}

/* ── Score ───────────────────────────────────── */
.score-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.score-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.score-bullet {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  margin-top: 8px;
  flex-shrink: 0;
}
</style>
