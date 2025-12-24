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
</script>

<template>
  <div class="panel glass">
    <div class="panel-title">出题配置</div>

    <div class="section">
      <div class="label">已选知识点：{{ selectedCount }}</div>
      <div class="kp-list" v-if="selectedKnowledgePoints.length">
        <el-tag v-for="kp in selectedKnowledgePoints" :key="kp.id" size="small" effect="plain" class="kp-tag">
          {{ kp.name }}
        </el-tag>
      </div>
      <div class="muted" v-else>请在左侧图谱中选择至少 1 个知识点</div>
    </div>

    <div class="section">
      <div class="label">题型</div>
      <el-select
        :model-value="questionType"
        @update:model-value="(v) => emit('update:questionType', v)"
        style="width: 100%"
      >
        <el-option label="单选题" value="single_choice" />
        <el-option label="多选题" value="multiple_choice" />
        <el-option label="填空题" value="fill_blank" />
        <el-option label="解答题" value="short_answer" />
      </el-select>
    </div>

    <div class="section">
      <div class="label">难度</div>
      <el-radio-group
        :model-value="difficulty"
        @update:model-value="(v) => emit('update:difficulty', v)"
        class="radios"
      >
        <el-radio-button label="easy">简单</el-radio-button>
        <el-radio-button label="medium">中等</el-radio-button>
        <el-radio-button label="hard">困难</el-radio-button>
      </el-radio-group>
    </div>

    <div class="section">
      <div class="label">数量</div>
      <el-input-number
        :model-value="count"
        :min="1"
        :max="7"
        :step="1"
        @update:model-value="(v) => emit('update:count', v)"
      />
      <div class="muted" style="margin-top: 8px">范围 1-7</div>
    </div>

    <el-button
      type="primary"
      size="large"
      :loading="generating"
      :disabled="selectedCount === 0"
      style="width: 100%; margin-top: 14px"
      @click="emit('generate')"
    >
      生成题目
    </el-button>
  </div>
</template>

<style scoped>
.panel {
  padding: 16px;
  border-radius: 16px;
}

.panel-title {
  font-weight: 650;
  letter-spacing: -0.01em;
}

.section {
  margin-top: 16px;
}

.label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 8px;
}

.kp-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kp-tag {
  border-radius: 999px;
}

.radios {
  width: 100%;
}
</style>
