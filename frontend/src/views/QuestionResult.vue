<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useCourseStore } from '../stores/course'
import { useQuestionStore } from '../stores/question'

const router = useRouter()
const courseStore = useCourseStore()
const questionStore = useQuestionStore()

const questions = computed(() => questionStore.generatedQuestions || [])

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

  await questionStore.generate(questionStore.lastGeneratePayload)
}

const courseName = computed(() => courseStore.currentCourse?.name || questionStore.courseId || '')
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
            <div class="answer">
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
