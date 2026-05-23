<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { workflowGraph } from '../api/agent'
import { useAgentStore } from '../stores/agent'

const store = useAgentStore()
const mermaidCode = ref('')
const errorMsg = ref('')
const loading = ref(true)

// 动态导入 mermaid（避免 SSR 问题）
onMounted(async () => {
  try {
    const res = await workflowGraph()
    if (res.error) {
      errorMsg.value = res.error
      return
    }
    mermaidCode.value = res.mermaid || ''

    // 等待 DOM 更新后渲染
    await import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        themeVariables: {
          primaryColor: '#EFF6FF',
          primaryTextColor: '#1E293B',
          primaryBorderColor: '#93C5FD',
          lineColor: '#94A3B8',
          secondaryColor: '#F1F5F9',
          tertiaryColor: '#F8FAFC',
        },
      })
      mermaid.render('workflow-mermaid', mermaidCode.value).then(({ svg }) => {
        document.getElementById('mermaid-output').innerHTML = svg
      }).catch((err) => {
        errorMsg.value = 'Mermaid 渲染失败: ' + err.message
      })
    })
  } catch (e) {
    errorMsg.value = e.message || '加载工作流图失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="container">
      <!-- Header -->
      <div class="page-header animate-fade-in-up">
        <button class="back-btn" @click="$router.push('/agent/draft')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          返回
        </button>
        <div>
          <h1 class="page-title">工作流图</h1>
          <p class="page-desc">LangGraph 多 Agent 协作流程的可视化展示</p>
        </div>
      </div>

      <!-- Mermaid Graph -->
      <div class="graph-card animate-fade-in-up" style="animation-delay: 60ms">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <span>正在加载工作流图...</span>
        </div>
        <div v-else-if="errorMsg" class="error-msg">
          {{ errorMsg }}
        </div>
        <div v-else id="mermaid-output" class="mermaid-container"></div>
      </div>

      <!-- Legend -->
      <div class="legend animate-fade-in-up" style="animation-delay: 120ms">
        <div class="legend-title">节点说明</div>
        <div class="legend-items">
          <div class="legend-item">
            <span class="legend-dot" style="background:#60A5FA"></span>
            <span>parse — Agent 1 解析 PDF</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background:#34D399"></span>
            <span>analyze — Agent 2 题槽分析</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background:#FBBF24"></span>
            <span>wait_slots — interrupt 暂停点（题槽确认）</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background:#F87171"></span>
            <span>generate — Agent 4 并行生成题目</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background:#A78BFA"></span>
            <span>kg_extract — Agent 1.5 知识图谱提取</span>
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
  padding-bottom: var(--space-12);
}

.container {
  max-width: 900px;
}

/* ── Header ─────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
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
  margin-top: 4px;
}
.back-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.page-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.page-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* ── Graph Card ─────────────────────────────── */
.graph-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-8);
  margin-bottom: var(--space-5);
  overflow-x: auto;
}

.loading {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-msg {
  color: var(--color-danger);
  font-size: 14px;
}

.mermaid-container {
  display: flex;
  justify-content: center;
  overflow-x: auto;
}
.mermaid-container :deep(svg) {
  max-width: 100%;
  height: auto;
}

/* ── Legend ─────────────────────────────── */
.legend {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-5) var(--space-6);
}

.legend-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-3);
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-6);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
