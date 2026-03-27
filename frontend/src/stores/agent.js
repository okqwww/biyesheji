import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAgentStore = defineStore('agent', () => {
  // ── 会话标识 ──────────────────────────────────────
  const sessionId = ref('')

  // ── Agent 1 输出 ──────────────────────────────────
  const parsedExams = ref([])

  // ── Agent 2 输出 ──────────────────────────────────
  const slotTemplate = ref([])

  // ── 用户设置 ──────────────────────────────────────
  /** "small" | "medium" | "large" */
  const modificationLevel = ref('medium')

  // ── Agent 4 输出 ──────────────────────────────────
  const generatedQuestions = ref([])

  // ── Agent 1.5 输出 ────────────────────────────────
  const kgStatus = ref('pending')
  const kgNodes = ref([])
  const kgEdges = ref([])

  // ── Loading 状态 ──────────────────────────────────
  const uploading = ref(false)
  const parsing = ref(false)
  const analyzing = ref(false)
  const generating = ref(false)
  const extractingKg = ref(false)

  // ── Actions ───────────────────────────────────────

  function reset() {
    sessionId.value = ''
    parsedExams.value = []
    slotTemplate.value = []
    modificationLevel.value = 'medium'
    generatedQuestions.value = []
    kgStatus.value = 'pending'
    kgNodes.value = []
    kgEdges.value = []
    uploading.value = false
    parsing.value = false
    analyzing.value = false
    generating.value = false
    extractingKg.value = false
  }

  /** 用新的单题结果替换对应 slot_id 的题目 */
  function replaceQuestion(slotId, newQuestion) {
    const idx = generatedQuestions.value.findIndex((q) => q.slot_id === slotId)
    if (idx !== -1) {
      generatedQuestions.value.splice(idx, 1, newQuestion)
    } else {
      generatedQuestions.value.push(newQuestion)
    }
  }

  return {
    sessionId,
    parsedExams,
    slotTemplate,
    modificationLevel,
    generatedQuestions,
    kgStatus,
    kgNodes,
    kgEdges,
    uploading,
    parsing,
    analyzing,
    generating,
    extractingKg,
    reset,
    replaceQuestion,
  }
})
