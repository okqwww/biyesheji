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

// 保存状态
const saving = ref(false)
const saved = ref(false)

// 判断是否为解答题
function isShortAnswer(question) {
  return question.type === 'short_answer' || question.type === '解答题'
}

// 检查文本是否包含代码（多行且有缩进）
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

  // 重置保存状态
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
    
    // 调用导出API，返回Markdown文本
    const markdown = await exportMarkdown(questions.value)
    
    // 创建Blob对象
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    
    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 生成文件名：题目_课程名_日期.md
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const filename = `题目_${courseName.value || '未知课程'}_${date}.md`
    link.download = filename
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    
    // 清理
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
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="header">
        <div>
          <div class="page-title">题目结果</div>
          <div class="page-subtitle">{{ courseName }} · 共 {{ questions.length }} 题</div>
        </div>
        <div class="actions">
          <el-button @click="goBack">返回</el-button>
          <el-button @click="exportQuestions">导出</el-button>
          <el-button 
            :type="saved ? 'success' : 'warning'" 
            :loading="saving" 
            @click="saveQuestionsToDb"
          >
            {{ saved ? '已保存' : '保存' }}
          </el-button>
          <el-button type="primary" :loading="questionStore.generating" @click="regenerate">重新生成</el-button>
        </div>
      </div>

      <el-empty v-if="questions.length === 0" description="暂无题目数据，请返回重新生成" />

      <div v-else class="list">
        <el-card v-for="(q, idx) in questions" :key="idx" class="q-card" shadow="never">
          <div class="q-top">
            <div class="q-index">第 {{ idx + 1 }} 题</div>
            <div class="q-tags">
              <el-tag size="small" effect="dark">{{ q.type }}</el-tag>
              <el-tag size="small" type="info" effect="plain">{{ q.difficulty }}</el-tag>
            </div>
          </div>

          <div class="q-block">
            <div class="q-label">题目</div>
            <div class="q-content">{{ q.content }}</div>
          </div>

          <div class="q-block" v-if="q.knowledge_points && q.knowledge_points.length">
            <div class="q-label">考察知识点</div>
            <div class="kp">
              <el-tag v-for="(kp, kIdx) in q.knowledge_points" :key="kIdx" size="small" effect="plain" class="kp-tag">
                {{ kp }}
              </el-tag>
            </div>
          </div>

          <div class="q-block" v-if="q.options && q.options.length">
            <div class="q-label">选项</div>
            <div class="options">
              <div v-for="(op, oIdx) in q.options" :key="oIdx" class="option">{{ op }}</div>
            </div>
          </div>

          <div class="q-block">
            <div class="q-label">参考答案</div>
            <!-- 解答题且包含代码块 -->
            <div v-if="isShortAnswer(q) && hasCodeBlock(q.answer)" class="answer-code">
              <pre><code>{{ q.answer }}</code></pre>
            </div>
            <!-- 普通答案 -->
            <div v-else class="answer">
              <span v-if="Array.isArray(q.answer)">{{ q.answer.join(', ') }}</span>
              <span v-else>{{ q.answer }}</span>
            </div>
          </div>

          <div class="q-block" v-if="q.explanation">
            <div class="q-label">解析</div>
            <div class="explain">{{ q.explanation }}</div>
          </div>

          <div class="q-block" v-if="q.scoring_points && q.scoring_points.length">
            <div class="q-label">评分点</div>
            <div class="score">
              <div v-for="(sp, sIdx) in q.scoring_points" :key="sIdx" class="score-item">- {{ sp }}</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.actions {
  display: flex;
  gap: 10px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.q-card {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.q-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.q-index {
  font-weight: 700;
  color: rgba(255, 255, 255, 0.82);
}

.q-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.q-block {
  margin-top: 14px;
  text-align: left;
}

.q-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  margin-bottom: 6px;
}

.q-content {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.82);
}

.options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option {
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.18);
  color: rgba(255, 255, 255, 0.82);
}

.answer {
  font-weight: 650;
  color: rgba(255, 255, 255, 0.82);
}

.answer-code {
  margin-top: 6px;
}

.answer-code pre {
  margin: 0;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.15);
  overflow-x: auto;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
}

.answer-code code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #e8eaed;
  white-space: pre;
  display: block;
  letter-spacing: 0.02em;
}

/* 代码块滚动条美化 */
.answer-code pre::-webkit-scrollbar {
  height: 8px;
}

.answer-code pre::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.answer-code pre::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.answer-code pre::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.explain,
.score {
  color: rgba(255, 255, 255, 0.82);
  white-space: pre-wrap;
  line-height: 1.8;
}

.kp {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kp-tag {
  border-radius: 999px;
}
</style>
