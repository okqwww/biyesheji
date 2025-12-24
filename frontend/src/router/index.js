import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import CourseSelect from '../views/CourseSelect.vue'
import KnowledgeGraph from '../views/KnowledgeGraph.vue'
import QuestionResult from '../views/QuestionResult.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    { path: '/courses', name: 'courses', component: CourseSelect },
    { path: '/courses/:courseId', name: 'graph', component: KnowledgeGraph, props: true },
    { path: '/result', name: 'result', component: QuestionResult },
  ],
})

export default router
