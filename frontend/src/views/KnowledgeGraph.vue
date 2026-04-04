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
      <!-- Header -->
      <div class="header animate-fade-in-up">
        <div class="header-left">
          <button class="back-btn" @click="goBack">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <div class="title-group">
            <div class="course-name">{{ courseStore.currentCourse?.name || courseId }}</div>
            <div class="course-hint muted">点击知识点选择考察范围，点击章节可批量选择</div>
          </div>
        </div>
        <div class="selection-badge" v-if="questionStore.selectedKnowledgePointIds.length > 0">
          <span class="badge-count">{{ questionStore.selectedKnowledgePointIds.length }}</span>
          <span class="badge-label">已选</span>
        </div>
      </div>

      <!-- Main Layout -->
      <div class="layout animate-fade-in-up" style="animation-delay: 60ms">
        <!-- Graph Area -->
        <div class="graph-area">
          <div class="graph-inner">
            <GraphView
              :nodes="nodes"
              :edges="edges"
              :selected-knowledge-point-ids="questionStore.selectedKnowledgePointIds"
              @toggle-knowledge-point="toggleKnowledgePoint"
              @toggle-chapter="toggleChapter"
            />
          </div>
        </div>

        <!-- Config Panel -->
        <div class="panel-area">
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
.page {
  min-height: 100vh;
  padding-top: var(--space-8);
  background: var(--color-bg);
}

/* ── Header ─────────────────────────────────── */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
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

.course-name {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.course-hint {
  font-size: 13px;
  margin-top: 2px;
}

.selection-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--color-primary-light);
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 122, 255, 0.2);
}

.badge-count {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-primary);
}

.badge-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
}

/* ── Layout ──────────────────────────────────── */
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-4);
  align-items: start;
}

.graph-area {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.graph-inner {
  padding: var(--space-3);
}

.panel-area {
  position: sticky;
  top: var(--space-4);
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .panel-area {
    position: static;
  }
}
</style>
