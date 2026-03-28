<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { startGenerate } from '../api/agent'
import LatexRenderer from '../components/LatexRenderer.vue'

const router = useRouter()
const store = useAgentStore()

const starting = ref(false)
const modLevel = ref(store.modificationLevel)

// 可编辑的题槽副本（深拷贝，避免直接改 store）
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
  // 深拷贝一份用于编辑
  editableSlots.value = JSON.parse(JSON.stringify(store.slotTemplate))
})

// ── 知识点标签编辑 ────────────────────────────────
const newKfInputs = ref({})  // { [slot_id]: string }

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
  // 将编辑后的题槽写回 store，并传给后端覆盖 session
  store.slotTemplate = JSON.parse(JSON.stringify(editableSlots.value))
  starting.value = true
  try {
    await startGenerate(store.sessionId, modLevel.value, editableSlots.value)
    store.generating = true
    router.push('/agent/draft')
  } catch {
    // http.js 已弹出错误
  } finally {
    starting.value = false
  }
}

function typeColor(type) {
  if (type?.includes('选择')) return '#818cf8'
  if (type?.includes('判断')) return '#34d399'
  if (type?.includes('填空')) return '#f59e0b'
  if (type?.includes('问答') || type?.includes('简答')) return '#60a5fa'
  if (type?.includes('计算') || type?.includes('解答') || type?.includes('大题')) return '#f87171'
  return '#a78bfa'
}
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="page-header">
        <el-button text @click="$router.push('/agent/parsing')">← 返回进度页</el-button>
        <h1 class="page-title">确认题槽结构</h1>
        <p class="page-desc">
          以下是 AI 从历年试卷中识别到的 <strong>{{ editableSlots.length }} 个题槽</strong>，每个题槽对应试卷中固定的一道题。
          可直接编辑题型、分值和知识点，确认无误后选择改动幅度并开始生成。
        </p>
      </div>

      <div class="slots-grid">
        <el-card
          v-for="slot in editableSlots"
          :key="slot.slot_id"
          class="slot-card glass"
          shadow="never"
        >
          <div class="slot-head">
            <div class="slot-type-badge" :style="{ background: typeColor(slot.type) + '22', color: typeColor(slot.type), borderColor: typeColor(slot.type) + '55' }">
              <!-- 题型可编辑 -->
              <el-input
                v-model="slot.type"
                size="small"
                class="type-input"
                :style="{ color: typeColor(slot.type) }"
              />
            </div>
            <div class="slot-meta">
              <!-- 分值可编辑 -->
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

          <!-- 知识点标签（可删除 + 新增） -->
          <div class="slot-kf">
            <el-tag
              v-for="kf in slot.knowledge_focus"
              :key="kf"
              size="small"
              type="info"
              effect="plain"
              closable
              class="kf-tag"
              @close="removeKf(slot, kf)"
            >{{ kf }}</el-tag>
            <div class="kf-add">
              <el-input
                v-model="newKfInputs[slot.slot_id]"
                size="small"
                placeholder="+ 添加知识点"
                class="kf-input"
                @keyup.enter="addKf(slot)"
              />
              <el-button size="small" text @click="addKf(slot)">添加</el-button>
            </div>
          </div>

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
        </el-card>
      </div>

      <!-- 底部操作区 -->
      <div class="bottom-panel glass">
        <div class="level-section">
          <div class="level-label">选择改动幅度</div>
          <el-radio-group v-model="modLevel" class="level-group">
            <el-radio-button
              v-for="opt in levelOptions"
              :key="opt.value"
              :value="opt.value"
              class="level-radio"
            >
              <div class="level-radio-inner">
                <div class="level-name">{{ opt.label }}</div>
                <div class="level-desc">{{ opt.desc }}</div>
              </div>
            </el-radio-button>
          </el-radio-group>
        </div>

        <el-button
          type="primary"
          size="large"
          :loading="starting"
          class="gen-btn"
          @click="generate"
        >
          {{ starting ? '启动中...' : `开始生成试卷（${levelOptions.find(o=>o.value===modLevel)?.label}）` }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 12px 0 8px;
}

.page-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.6;
  margin: 0;
}

.page-desc strong {
  color: #818cf8;
}

/* 题槽网格 */
.slots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 100px;
}

.slot-card {
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.slot-card :deep(.el-card__body) {
  padding: 18px;
}

.slot-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.slot-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid;
  font-size: 13px;
  font-weight: 600;
}

.slot-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.slot-points {
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
}

.slot-kf {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.kf-tag {
  font-size: 12px;
}

/* 题型输入框 */
.type-input {
  width: 120px;
}

.type-input :deep(.el-input__wrapper) {
  background: transparent;
  box-shadow: none;
  padding: 0 4px;
}

.type-input :deep(.el-input__inner) {
  color: inherit;
  font-size: 13px;
  font-weight: 600;
  height: 24px;
}

/* 分值输入框 */
.points-input {
  width: 80px;
}

.points-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: none;
}

.points-input :deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 700;
}

.points-unit {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

/* 知识点新增区 */
.kf-add {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.kf-input {
  width: 120px;
}

.kf-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
}

.kf-input :deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}

.history-collapse :deep(.el-collapse) {
  border: none;
  background: transparent;
}

.history-collapse :deep(.el-collapse-item__header) {
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0;
  height: 36px;
}

.history-collapse :deep(.el-collapse-item__wrap) {
  background: transparent;
  border: none;
}

.history-collapse :deep(.el-collapse-item__content) {
  background: transparent;
  padding: 12px 0 0;
  color: rgba(255, 255, 255, 0.7);
}

.history-item {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.history-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.history-year {
  font-size: 12px;
  font-weight: 600;
  color: #818cf8;
  margin-bottom: 4px;
}

.history-content {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 底部面板 */
.bottom-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 32px;
  background: rgba(15, 15, 25, 0.92);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  z-index: 100;
}

.level-section {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.level-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  font-weight: 500;
}

.level-group {
  display: flex;
  gap: 8px;
}

.level-radio :deep(.el-radio-button__inner) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
  padding: 6px 14px;
  height: auto;
  border-radius: 8px !important;
}

.level-radio-inner {
  text-align: left;
}

.level-name {
  font-size: 13px;
  font-weight: 600;
}

.level-desc {
  font-size: 11px;
  opacity: 0.65;
  margin-top: 2px;
  max-width: 160px;
  white-space: normal;
  line-height: 1.3;
}

.gen-btn {
  height: 44px;
  padding: 0 28px;
  border-radius: 10px;
  white-space: nowrap;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .bottom-panel {
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
