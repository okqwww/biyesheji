<script setup>
import { useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent'

const router = useRouter()
const agentStore = useAgentStore()

function goStart() {
  router.push('/courses')
}

function goAgent() {
  agentStore.reset()
  router.push('/agent/upload')
}
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="hero">
        <div class="hero-badge">IQGS · Intelligent Question Generation System</div>
        <h1 class="hero-title">基于大模型与知识图谱的智能出题系统</h1>
        <p class="hero-subtitle">
          面向高校教师的智能出题辅助工具：可视化选择考察范围，结合大模型生成高质量题目、参考答案与评分点。
        </p>

        <div class="hero-actions">
          <el-button type="primary" size="large" class="cta" @click="goStart">
            根据知识图谱生题
          </el-button>
          <el-button type="success" size="large" class="cta cta-agent" @click="goAgent">
            根据往年题智能出题 (Agent)
          </el-button>
        </div>
        <div class="mode-hint">
          <span class="hint-item">
            <strong>知识图谱生题</strong>：快速生成练习题，无需往年题
          </span>
          <span class="hint-sep">·</span>
          <span class="hint-item">
            <strong>往年题智能出题</strong>：上传历年真题 PDF，多 Agent 生成高质量试卷
          </span>
        </div>

        <div class="features">
          <div class="feature glass">
            <div class="feature-title">高效</div>
            <div class="feature-desc">从选知识点到生成题目，一次完成。</div>
          </div>
          <div class="feature glass">
            <div class="feature-title">可控</div>
            <div class="feature-desc">题型、难度、数量可配置，支持编辑与选择性保存。</div>
          </div>
          <div class="feature glass">
            <div class="feature-title">结构化</div>
            <div class="feature-desc">知识图谱驱动，确保覆盖关键知识点。</div>
          </div>
        </div>
      </div>

      <div class="footer muted">© 2026 北京邮电大学 周奕君 智能出题系统 · FastAPI + Neo4j + DeepSeek</div>
    </div>
  </div>
</template>

<style scoped>
.hero {
  padding: 64px 28px 28px;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 40px 120px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  position: relative;
}

.hero:before {
  content: '';
  position: absolute;
  inset: -1px;
  background: radial-gradient(600px 240px at 30% 0%, rgba(99, 102, 241, 0.4), transparent 60%),
    radial-gradient(520px 240px at 75% 20%, rgba(16, 185, 129, 0.3), transparent 60%);
  opacity: 0.9;
  pointer-events: none;
}

.hero > * {
  position: relative;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.86);
  font-size: 12px;
  letter-spacing: 0.06em;
}

.hero-title {
  margin: 18px 0 0;
  font-size: 44px;
  line-height: 1.06;
  letter-spacing: -0.03em;
}

.hero-subtitle {
  margin: 16px 0 0;
  color: rgba(255, 255, 255, 0.75);
  font-size: 16px;
  max-width: 760px;
}

.hero-actions {
  margin-top: 26px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.cta {
  height: 42px;
  padding: 0 18px;
  border-radius: 12px;
}

.cta-agent {
  padding: 0 22px;
}

.mode-hint {
  margin-top: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hint-sep {
  opacity: 0.4;
}

.hint-item strong {
  color: rgba(255, 255, 255, 0.85);
}

.features {
  margin-top: 32px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.feature {
  padding: 16px 16px;
  text-align: left;
}

.feature-title {
  font-weight: 650;
  letter-spacing: -0.01em;
}

.feature-desc {
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
}

.footer {
  margin-top: 20px;
  text-align: center;
  font-size: 12px;
}

@media (max-width: 980px) {
  .features {
    grid-template-columns: 1fr;
  }
  .hero-title {
    font-size: 34px;
  }
  .hero-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
