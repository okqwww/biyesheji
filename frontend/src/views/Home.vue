<script setup>
import { useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent'

const router = useRouter()
const agentStore = useAgentStore()

function goKnowledgeGraph() {
  router.push('/courses')
}

function goAgent() {
  agentStore.reset()
  router.push('/agent/upload')
}
</script>

<template>
  <div class="page">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-badge animate-fade-in-up" style="animation-delay: 0ms">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
        IQGS · 智能出题系统
      </div>

      <h1 class="hero-title animate-fade-in-up" style="animation-delay: 80ms">
        基于大模型与<br>知识图谱的智能出题系统
      </h1>

      <p class="hero-subtitle animate-fade-in-up" style="animation-delay: 160ms">
        面向高校教师的智能出题辅助工具<br>
        可视化选择考察范围，结合大模型生成高质量题目
      </p>

      <!-- Entry Modes -->
      <div class="entry-grid animate-fade-in-up" style="animation-delay: 240ms">
        <button class="entry-card entry-card--primary" @click="goKnowledgeGraph">
          <div class="entry-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="4" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="20" cy="6" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="4" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="20" cy="18" r="2" stroke="currentColor" stroke-width="1.5"/>
              <line x1="6" y1="6" x2="9.5" y2="10" stroke="currentColor" stroke-width="1.5"/>
              <line x1="18" y1="6" x2="14.5" y2="10" stroke="currentColor" stroke-width="1.5"/>
              <line x1="6" y1="18" x2="9.5" y2="14" stroke="currentColor" stroke-width="1.5"/>
              <line x1="18" y1="18" x2="14.5" y2="14" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </div>
          <div class="entry-content">
            <div class="entry-title">根据知识图谱生题</div>
            <div class="entry-desc">从课程知识图谱中选择考察范围，快速生成练习题目</div>
          </div>
          <div class="entry-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </button>

        <button class="entry-card entry-card--agent" @click="goAgent">
          <div class="entry-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/>
              <path d="M9 9L6 15L9 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M15 9L18 15L15 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <line x1="12" y1="12" x2="12" y2="12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="entry-content">
            <div class="entry-title">往年题智能出题 <span class="badge-agent">Agent</span></div>
            <div class="entry-desc">上传历年真题 PDF，多 Agent 协作生成高质量新试卷</div>
          </div>
          <div class="entry-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </button>
      </div>
    </section>

    <!-- Feature Strip -->
    <section class="features animate-fade-in-up" style="animation-delay: 360ms">
      <div class="feature-item">
        <div class="feature-dot feature-dot--blue"></div>
        <div>
          <div class="feature-title">高效</div>
          <div class="feature-desc">从选知识点到生成题目，一次完成</div>
        </div>
      </div>
      <div class="feature-divider"></div>
      <div class="feature-item">
        <div class="feature-dot feature-dot--green"></div>
        <div>
          <div class="feature-title">可控</div>
          <div class="feature-desc">题型、难度、数量可配置</div>
        </div>
      </div>
      <div class="feature-divider"></div>
      <div class="feature-item">
        <div class="feature-dot feature-dot--purple"></div>
        <div>
          <div class="feature-title">结构化</div>
          <div class="feature-desc">知识图谱驱动，确保覆盖关键知识点</div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <span>© 2026 北京邮电大学 周奕君</span>
      <span class="footer-sep">·</span>
      <span>FastAPI + Neo4j + DeepSeek</span>
    </footer>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-6);
  background: var(--color-bg);
}

/* ── Hero ──────────────────────────────────────── */
.hero {
  text-align: center;
  max-width: 680px;
  padding: var(--space-16) 0 var(--space-12);
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-6);
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(36px, 6vw, 52px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--color-text);
  margin-bottom: var(--space-5);
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-10);
}

/* ── Entry Cards ──────────────────────────────── */
.entry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  text-align: left;
}

.entry-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.entry-card::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity var(--transition-base);
}

.entry-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-border);
}

.entry-card:active {
  transform: translateY(0);
}

.entry-card--primary::before {
  background: linear-gradient(135deg, rgba(0, 122, 255, 0.04), transparent);
}

.entry-card--primary:hover::before {
  opacity: 1;
}

.entry-card--agent::before {
  background: linear-gradient(135deg, rgba(52, 199, 89, 0.04), transparent);
}

.entry-card--agent:hover::before {
  opacity: 1;
}

.entry-icon {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
}

.entry-card--primary .entry-icon {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.entry-card--agent .entry-icon {
  background: #E8F8EE;
  color: var(--color-success);
}

.entry-content {
  flex: 1;
  min-width: 0;
}

.entry-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.entry-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.entry-arrow {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  transition: transform var(--transition-fast), color var(--transition-fast);
}

.entry-card:hover .entry-arrow {
  transform: translateX(3px);
  color: var(--color-primary);
}

.badge-agent {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: var(--radius-full);
  background: #E8F8EE;
  color: var(--color-success);
  font-size: 11px;
  font-weight: 600;
}

/* ── Features ─────────────────────────────────── */
.features {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-6) var(--space-8);
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-12);
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.feature-dot--blue { background: var(--color-primary); }
.feature-dot--green { background: var(--color-success); }
.feature-dot--purple { background: #AF52DE; }

.feature-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.feature-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.feature-divider {
  width: 1px;
  height: 36px;
  background: var(--color-border-light);
}

/* ── Footer ──────────────────────────────────── */
.footer {
  font-size: 12px;
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.footer-sep {
  opacity: 0.5;
}

/* ── Responsive ───────────────────────────────── */
@media (max-width: 640px) {
  .entry-grid {
    grid-template-columns: 1fr;
  }

  .features {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .feature-divider {
    width: 100%;
    height: 1px;
  }

  .hero {
    padding: var(--space-10) 0 var(--space-8);
  }
}
</style>
