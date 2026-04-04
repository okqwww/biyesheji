<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCourseStore } from '../stores/course'

const router = useRouter()
const courseStore = useCourseStore()

onMounted(() => {
  courseStore.fetchCourses()
})

function goCourse(courseId) {
  router.push(`/courses/${courseId}`)
}

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="page">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header animate-fade-in-up">
        <h1 class="page-heading">选择课程</h1>
        <p class="page-desc">选择要出题的课程，进入知识图谱页面进行知识点选择与出题配置。</p>
      </div>

      <!-- Course Grid -->
      <div class="course-grid">
        <el-skeleton v-if="courseStore.loadingCourses" :rows="5" animated />

        <template v-else>
          <button
            v-for="c in courseStore.courses"
            :key="c.id"
            class="course-card animate-fade-in-up"
            @click="goCourse(c.id)"
          >
            <div class="course-card__body">
              <div class="course-name">{{ c.name }}</div>
              <div class="course-desc">{{ c.description }}</div>
            </div>
            <div class="course-card__footer">
              <span class="course-kp-count">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="4" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="20" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="4" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="20" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
                  <line x1="6" y1="6" x2="8.5" y2="9.5" stroke="currentColor" stroke-width="1.5"/>
                  <line x1="18" y1="6" x2="15.5" y2="9.5" stroke="currentColor" stroke-width="1.5"/>
                  <line x1="6" y1="18" x2="8.5" y2="14.5" stroke="currentColor" stroke-width="1.5"/>
                  <line x1="18" y1="18" x2="15.5" y2="14.5" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                {{ c.knowledge_point_count }} 个知识点
              </span>
              <span class="course-id">ID: {{ c.id }}</span>
            </div>
            <div class="course-card__arrow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </button>

          <el-empty v-if="courseStore.courses.length === 0" description="暂无课程数据" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-top: var(--space-12);
  background: var(--color-bg);
}

/* ── Page Header ────────────────────────────── */
.page-header {
  margin-bottom: var(--space-10);
}

.page-heading {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.page-desc {
  font-size: 15px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* ── Course Grid ─────────────────────────────── */
.course-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

/* ── Course Card ─────────────────────────────── */
.course-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  text-align: left;
  position: relative;
  transition: all var(--transition-base);
  overflow: hidden;
}

.course-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 122, 255, 0.03), transparent);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.course-card:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-2px);
  border-color: var(--color-border);
}

.course-card:hover::before {
  opacity: 1;
}

.course-card:active {
  transform: translateY(0);
}

.course-card__body {
  flex: 1;
  margin-bottom: var(--space-5);
}

.course-name {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.course-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.course-kp-count {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  padding: 3px 10px;
  background: var(--color-primary-light);
  border-radius: var(--radius-full);
}

.course-id {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.course-card__arrow {
  position: absolute;
  right: var(--space-5);
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
}

.course-card:hover .course-card__arrow {
  color: var(--color-primary);
  transform: translateY(-50%) translateX(2px);
}

/* ── Responsive ───────────────────────────────── */
@media (max-width: 640px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
