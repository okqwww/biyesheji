<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { workflowResume } from '../api/agent'
import LatexRenderer from '../components/LatexRenderer.vue'

const router = useRouter()
const store = useAgentStore()

const starting = ref(false)
const modLevel = ref(store.modificationLevel)

const editableSlots = ref([])

const levelOptions = [
  { label: '小改', value: 'small', desc: '保留原题框架，仅微调数值或条件' },
  { label: '中改', value: 'medium', desc: '改变解题方向或应用场景，知识点相同' },
  { label: '大改', value: 'large', desc: '深度重构，考察相同知识点的全新题目' },
]

onMounted(() => {
  if (!store.sessionId || !store.slotTemplate?.length) {
    ElMessage.warning('请先完成 PDF 解析与分析')
    router.replace('/agent/upload')
    return
  }
  editableSlots.value = JSON.parse(JSON.stringify(store.slotTemplate))
})

const newKfInputs = ref({})

function addKf(slot) {
  const val = (newKfInputs.value[slot.slot_id] || '').trim()
  if (!val) return
  if (!slot.knowledge_focus) slot.knowledge_focus = []
  if (!slot.knowledge_focus.includes(val)) slot.knowledge_focus.push(val)
  newKfInputs.value[slot.slot_id] = ''
}

function removeKf(slot, kf) {
  slot.knowledge_focus = slot.knowledge_focus.filter((k) => k !== kf)
}

async function generate() {
  store.modificationLevel = modLevel.value
  const confirmedSlots = JSON.parse(JSON.stringify(editableSlots.value))
  starting.value = true
  try {
    // 调用 workflow/resume 批准题槽，继续 generate → kg_extract
    await workflowResume(store.sessionId, true, modLevel.value, confirmedSlots)
    store.generating = true
    router.push('/agent/draft')
  } catch {
    // http.js already shows error
  } finally {
    starting.value = false
  }
}

function typeColor(type) {
  if (type?.includes('选择')) return '#007AFF'
  if (type?.includes('判断')) return '#34C759'
  if (type?.includes('填空')) return '#FF9500'
  if (type?.includes('问答') || type?.includes('简答')) return '#AF52DE'
  if (type?.includes('计算') || type?.includes('解答') || type?.includes('大题')) return '#FF3B30'
  return '#86868B'
}
</script>

<template>
  <div class="page">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header animate-fade-in-up">
        <button class="back-btn" @click="$router.push('/agent/parsing')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          返回
        </button>
        <div>
          <h1 class="page-title">确认题槽结构</h1>
          <p class="page-desc">
            以下是 AI 从历年试卷中识别到的 <strong>{{ editableSlots.length }} 个题槽</strong>，可直接编辑确认。
          </p>
        </div>
      </div>

      <!-- Slots Grid -->
      <div class="slots-grid">
        <div
          v-for="(slot, idx) in editableSlots"
          :key="slot.slot_id"
          class="slot-card animate-fade-in-up"
          :style="{ animationDelay: `${idx * 50}ms` }"
        >
          <!-- Slot Header -->
          <div class="slot-header">
            <div class="slot-type" :style="{ background: typeColor(slot.type) + '18', color: typeColor(slot.type), borderColor: typeColor(slot.type) + '30' }">
              <el-input
                v-model="slot.type"
                size="small"
                class="type-input"
                :style="{ color: typeColor(slot.type) }"
              />
            </div>
            <div class="slot-points">
              <el-input-number
                v-model="slot.points"
                :min="1"
                :max="200"
                size="small"
                controls-position="right"
                class="points-input"
              />
              <span class="points-unit">分</span>
            </div>
          </div>

          <!-- Knowledge Focus Tags -->
          <div class="slot-kf">
            <span
              v-for="kf in slot.knowledge_focus"
              :key="kf"
              class="kf-chip"
            >
              {{ kf }}
              <button class="kf-remove" @click="removeKf(slot, kf)">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                  <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </span>
            <div class="kf-add">
              <el-input
                v-model="newKfInputs[slot.slot_id]"
                size="small"
                placeholder="添加知识点"
                class="kf-input"
                @keyup.enter="addKf(slot)"
              />
              <button class="kf-add-btn" @click="addKf(slot)">添加</button>
            </div>
          </div>

          <!-- History -->
          <el-collapse v-if="slot.history?.length" class="history-collapse">
            <el-collapse-item :title="`历年题目（${slot.history.length} 题）`">
              <div
                v-for="h in slot.history"
                :key="h.year"
                class="history-item"
              >
                <div class="history-year">{{ h.year && h.year !== '未知年份' ? h.year + ' 年' : '未知年' }}</div>
                <LatexRenderer :content="h.content" class="history-content" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- Bottom Action Bar -->
      <div class="bottom-bar animate-fade-in">
        <div class="level-section">
          <div class="level-label">改动幅度</div>
          <div class="level-options">
            <button
              v-for="opt in levelOptions"
              :key="opt.value"
              class="level-btn"
              :class="{ 'level-btn--active': modLevel === opt.value }"
              @click="modLevel = opt.value"
            >
              <div class="level-name">{{ opt.label }}</div>
              <div class="level-desc">{{ opt.desc }}</div>
            </button>
          </div>
        </div>

        <button
          class="gen-btn"
          :class="{ 'gen-btn--active': !starting }"
          :disabled="starting"
          @click="generate"
        >
          <span v-if="starting" class="spinner"></span>
          开始生成试卷（{{ levelOptions.find(o => o.value === modLevel)?.label }}）
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-top: var(--space-10);
  background: var(--color-bg);
  padding-bottom: 120px;
}

/* ── Page Header ────────────────────────────── */
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

.page-desc strong {
  color: var(--color-primary);
}

/* ── Slots Grid ─────────────────────────────── */
.slots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

/* ── Slot Card ─────────────────────────────── */
.slot-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-5);
  transition: box-shadow var(--transition-base);
}

.slot-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.slot-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.slot-type {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid;
  font-size: 13px;
  font-weight: 600;
}

.type-input {
  width: 110px;
}

.type-input :deep(.el-input__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 4px;
}

.type-input :deep(.el-input__inner) {
  color: inherit !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  height: 24px !important;
}

.slot-points {
  display: flex;
  align-items: center;
  gap: 6px;
}

.points-input {
  width: 72px;
}

.points-input :deep(.el-input__wrapper) {
  background: var(--color-bg-secondary) !important;
  box-shadow: none !important;
  border-radius: 6px !important;
}

.points-input :deep(.el-input__inner) {
  color: var(--color-text) !important;
  font-weight: 700 !important;
  text-align: center !important;
}

.points-unit {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* ── Knowledge Focus ─────────────────────────── */
.slot-kf {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--space-3);
}

.kf-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
}

.kf-remove {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity var(--transition-fast);
  background: none;
  border: none;
  padding: 0;
  color: inherit;
}

.kf-remove:hover {
  opacity: 1;
}

.kf-add {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kf-input {
  width: 110px;
}

.kf-input :deep(.el-input__wrapper) {
  background: var(--color-bg-secondary) !important;
  box-shadow: none !important;
  border-radius: 6px !important;
}

.kf-input :deep(.el-input__inner) {
  color: var(--color-text-secondary) !important;
  font-size: 12px !important;
}

.kf-add-btn {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
}

/* ── History ─────────────────────────────────── */
.history-collapse {
  margin-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  padding-top: var(--space-3);
}

.history-item {
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border-light);
}

.history-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.history-year {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.history-content {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Bottom Bar ─────────────────────────────── */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: var(--space-4) var(--space-6);
  background: rgba(250, 250, 250, 0.92);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  z-index: 100;
}

.level-section {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
}

.level-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.level-options {
  display: flex;
  gap: var(--space-2);
}

.level-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  border: 1.5px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--transition-fast);
  min-width: 120px;
}

.level-btn:hover {
  border-color: var(--color-border);
}

.level-btn--active {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.level-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.level-btn--active .level-name {
  color: var(--color-primary);
}

.level-desc {
  font-size: 11px;
  color: var(--color-text-tertiary);
  white-space: normal;
  line-height: 1.3;
}

.gen-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border: none;
  cursor: not-allowed;
  transition: all var(--transition-base);
  white-space: nowrap;
  flex-shrink: 0;
}

.gen-btn--active {
  background: var(--color-primary);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.gen-btn--active:hover {
  background: var(--color-primary-hover);
  box-shadow: 0 4px 16px rgba(0, 122, 255, 0.35);
  transform: translateY(-1px);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .bottom-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .level-section {
    flex-direction: column;
    align-items: flex-start;
  }

  .slots-grid {
    grid-template-columns: 1fr;
  }
}
</style>
