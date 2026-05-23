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
    // ── Agent 出题流程 ─────────────────────────────────
    { path: '/agent/upload', name: 'agent-upload', component: () => import('../views/AgentUpload.vue') },
    { path: '/agent/parsing', name: 'agent-parsing', component: () => import('../views/AgentParsing.vue') },
    { path: '/agent/slots', name: 'agent-slots', component: () => import('../views/AgentSlots.vue') },
    { path: '/agent/draft', name: 'agent-draft', component: () => import('../views/AgentDraft.vue') },
    { path: '/agent/graph', name: 'agent-graph', component: () => import('../views/AgentGraph.vue') },
    { path: '/agent/workflow-graph', name: 'agent-workflow-graph', component: () => import('../views/AgentWorkflowGraph.vue') },
  ],
})

export default router
