<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import GraphView from '../components/GraphView.vue'
import ConfigPanel from '../components/ConfigPanel.vue'
import { useCourseStore } from '../stores/course'
import { useQuestionStore } from '../stores/question'

const route = useRoute()
const router = useRouter()

const courseStore = useCourseStore()
const questionStore = useQuestionStore()

const courseId = computed(() => route.params.courseId)

onMounted(async () => {
  await courseStore.fetchCourses()
  await courseStore.fetchCourseGraph(courseId.value)
  questionStore.courseId = courseId.value
})

const nodes = computed(() => courseStore.graphNodes)
const edges = computed(() => courseStore.graphEdges)

const knowledgePointNodes = computed(() => nodes.value.filter((n) => n.type === 'knowledge_point'))

const selectedKnowledgePoints = computed(() => {
  const set = new Set(questionStore.selectedKnowledgePointIds)
  return knowledgePointNodes.value.filter((kp) => set.has(kp.id))
})

const chapterToKps = computed(() => {
  const map = new Map()
  for (const e of edges.value) {
    if (e.type !== 'contains') continue
    if (!map.has(e.source)) map.set(e.source, [])
    map.get(e.source).push(e.target)
  }
  return map
})

function toggleKnowledgePoint(kpId) {
  questionStore.toggleKnowledgePointId(kpId)
}

function toggleChapter(chapterId) {
  const kpIds = chapterToKps.value.get(chapterId) || []
  if (kpIds.length === 0) return

  const set = new Set(questionStore.selectedKnowledgePointIds)
  const allSelected = kpIds.every((id) => set.has(id))
  if (allSelected) {
    for (const id of kpIds) set.delete(id)
  } else {
    for (const id of kpIds) set.add(id)
  }
  questionStore.setSelectedKnowledgePointIds(Array.from(set))
}

async function onGenerate() {
  const payload = {
    course_id: courseId.value,
    knowledge_point_ids: questionStore.selectedKnowledgePointIds,
    question_type: questionStore.questionType,
    difficulty: questionStore.difficulty,
    count: questionStore.count,
  }

  await questionStore.generate(payload)
  if (!questionStore.generatedQuestions.length) return

  router.push('/result')
}

async function goBack() {
  if (questionStore.generating) return

  const hasSelection = questionStore.selectedKnowledgePointIds.length > 0
  if (!hasSelection) {
    router.push('/courses')
    return
  }

  try {
    await ElMessageBox.confirm('确认返回课程选择页？已选知识点将会保留在当前会话中。', '提示', {
      confirmButtonText: '返回',
      cancelButtonText: '取消',
      type: 'warning',
    })
    router.push('/courses')
  } catch {
    // ignore
  }
}
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="header">
        <div class="left">
          <el-button text @click="goBack">← 返回</el-button>
          <div class="title">
            <div class="name">{{ courseStore.currentCourse?.name || courseId }}</div>
            <div class="muted">点击知识点选择考察范围，点击章节可批量选择/取消</div>
          </div>
        </div>
        <el-tag effect="dark" size="small">已选 {{ questionStore.selectedKnowledgePointIds.length }}</el-tag>
      </div>

      <div class="layout">
        <div class="graph glass">
          <GraphView
            :nodes="nodes"
            :edges="edges"
            :selected-knowledge-point-ids="questionStore.selectedKnowledgePointIds"
            @toggle-knowledge-point="toggleKnowledgePoint"
            @toggle-chapter="toggleChapter"
          />
        </div>

        <div class="panel">
          <ConfigPanel
            :selected-knowledge-points="selectedKnowledgePoints"
            :question-type="questionStore.questionType"
            :difficulty="questionStore.difficulty"
            :count="questionStore.count"
            :generating="questionStore.generating"
            @update:questionType="(v) => (questionStore.questionType = v)"
            @update:difficulty="(v) => (questionStore.difficulty = v)"
            @update:count="(v) => (questionStore.count = v)"
            @generate="onGenerate"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title .name {
  font-weight: 700;
  letter-spacing: -0.01em;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 14px;
}

.graph {
  padding: 12px;
}

.panel {
  position: sticky;
  top: 14px;
  height: fit-content;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .panel {
    position: static;
  }
}
</style>
