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
      <div class="topbar">
        <el-button text @click="goHome">← 返回首页</el-button>
      </div>

      <h1 class="page-title">选择课程</h1>
      <p class="page-subtitle">选择要出题的课程，进入知识图谱页面进行知识点选择与出题配置。</p>

      <div class="course-grid">
        <el-skeleton v-if="courseStore.loadingCourses" :rows="6" animated class="glass" style="padding: 18px" />

        <template v-else>
          <el-card
            v-for="c in courseStore.courses"
            :key="c.id"
            class="course-card"
            shadow="never"
            @click="goCourse(c.id)"
          >
            <div class="course-name">{{ c.name }}</div>
            <div class="course-desc muted">{{ c.description }}</div>
            <div class="course-meta">
              <el-tag size="small" effect="dark">知识点 {{ c.knowledge_point_count }}</el-tag>
              <el-tag size="small" type="info" effect="plain">ID: {{ c.id }}</el-tag>
            </div>
          </el-card>

          <el-empty v-if="courseStore.courses.length === 0" description="暂无课程数据" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.topbar {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 16px;
}

.course-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.course-card {
  cursor: pointer;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.course-card:hover {
  border-color: rgba(255, 255, 255, 0.22);
}

.course-name {
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: rgba(255, 255, 255, 0.82);
}

.course-desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.82);
}

.course-meta {
  margin-top: 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 980px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
