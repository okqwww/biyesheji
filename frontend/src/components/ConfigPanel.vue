<script setup>
import { computed } from 'vue'

const props = defineProps({
  selectedKnowledgePoints: { type: Array, default: () => [] },
  questionType: { type: String, default: 'single_choice' },
  difficulty: { type: String, default: 'medium' },
  count: { type: Number, default: 3 },
  generating: { type: Boolean, default: false },
})

const emit = defineEmits(['update:questionType', 'update:difficulty', 'update:count', 'generate'])

const selectedCount = computed(() => props.selectedKnowledgePoints.length)

const questionTypeOptions = [
  { label: '单选题', value: 'single_choice' },
  { label: '多选题', value: 'multiple_choice' },
  { label: '填空题', value: 'fill_blank' },
  { label: '解答题', value: 'short_answer' },
]

const difficultyOptions = [
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]

const questionTypeLabel = computed(() => {
  return questionTypeOptions.find(o => o.value === props.questionType)?.label || '单选题'
})
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">出题配置</div>
    </div>

    <!-- Selected Knowledge Points -->
    <div class="section">
      <div class="section-label">已选知识点</div>
      <div class="kp-count" :class="{ 'kp-count--active': selectedCount > 0 }">
        <span class="kp-number">{{ selectedCount }}</span>
        <span class="kp-text">个知识点</span>
      </div>
      <div class="kp-list" v-if="selectedKnowledgePoints.length">
        <span
          v-for="kp in selectedKnowledgePoints"
          :key="kp.id"
          class="kp-chip"
        >
          {{ kp.name }}
        </span>
      </div>
      <div class="kp-empty" v-else>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        请在左侧图谱中选择知识点
      </div>
    </div>

    <div class="divider"></div>

    <!-- Question Type -->
    <div class="section">
      <div class="section-label">题型</div>
      <el-select
        :model-value="questionType"
        @update:model-value="(v) => emit('update:questionType', v)"
        style="width: 100%"
        :placeholder="questionTypeLabel"
      >
        <el-option
          v-for="opt in questionTypeOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>

    <!-- Difficulty -->
    <div class="section">
      <div class="section-label">难度</div>
      <div class="radio-group">
        <button
          v-for="opt in difficultyOptions"
          :key="opt.value"
          class="radio-btn"
          :class="{ 'radio-btn--active': difficulty === opt.value }"
          @click="emit('update:difficulty', opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- Count -->
    <div class="section">
      <div class="section-label">数量</div>
      <div class="count-control">
        <button
          class="count-btn"
          :disabled="count <= 1"
          @click="emit('update:count', Math.max(1, count - 1))"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
        <span class="count-number">{{ count }}</span>
        <button
          class="count-btn"
          :disabled="count >= 7"
          @click="emit('update:count', Math.min(7, count + 1))"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
      <div class="count-hint">范围 1-7</div>
    </div>

    <!-- Generate Button -->
    <button
      class="generate-btn"
      :class="{ 'generate-btn--active': selectedCount > 0 && !generating }"
      :disabled="selectedCount === 0 || generating"
      @click="emit('generate')"
    >
      <svg v-if="!generating" width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      </svg>
      <span v-if="generating" class="spinner"></span>
      {{ generating ? '生成中...' : '生成题目' }}
    </button>
  </div>
</template>

<style scoped>
.panel {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-5);
}

.panel-header {
  margin-bottom: var(--space-4);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.section {
  margin-bottom: var(--space-4);
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
}

/* ── KP Count ─────────────────────────────── */
.kp-count {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: var(--space-3);
}

.kp-count--active .kp-number {
  color: var(--color-primary);
}

.kp-number {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-tertiary);
  line-height: 1;
}

.kp-text {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.kp-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kp-chip {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kp-empty {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-tertiary);
  padding: var(--space-2) 0;
}

/* ── Divider ─────────────────────────────── */
.divider {
  height: 1px;
  background: var(--color-border-light);
  margin: var(--space-4) 0;
}

/* ── Radio Group ─────────────────────────── */
.radio-group {
  display: flex;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 2px;
}

.radio-btn {
  flex: 1;
  padding: 7px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
}

.radio-btn:hover {
  color: var(--color-text);
}

.radio-btn--active {
  background: var(--color-bg-card);
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* ── Count Control ─────────────────────────── */
.count-control {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  width: fit-content;
}

.count-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: none;
  border: none;
}

.count-btn:hover:not(:disabled) {
  background: var(--color-bg-card);
  color: var(--color-primary);
}

.count-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.count-number {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  min-width: 24px;
  text-align: center;
}

.count-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}

/* ── Generate Button ───────────────────────── */
.generate-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border: none;
  cursor: not-allowed;
  transition: all var(--transition-base);
  margin-top: var(--space-2);
}

.generate-btn--active {
  background: var(--color-primary);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.generate-btn--active:hover {
  background: var(--color-primary-hover);
  box-shadow: 0 4px 16px rgba(0, 122, 255, 0.35);
  transform: translateY(-1px);
}

.generate-btn--active:active {
  transform: translateY(0);
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
</style>
