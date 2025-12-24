import { defineStore } from 'pinia'
import { generateQuestions } from '../api/questions'

export const useQuestionStore = defineStore('question', {
  state: () => ({
    courseId: null,
    selectedKnowledgePointIds: [],
    questionType: 'single_choice',
    difficulty: 'medium',
    count: 3,
    generating: false,
    generatedQuestions: [],
    lastGeneratePayload: null,
  }),
  actions: {
    setSelectedKnowledgePointIds(ids) {
      this.selectedKnowledgePointIds = Array.isArray(ids) ? ids : []
    },
    toggleKnowledgePointId(id) {
      const set = new Set(this.selectedKnowledgePointIds)
      if (set.has(id)) set.delete(id)
      else set.add(id)
      this.selectedKnowledgePointIds = Array.from(set)
    },
    setConfig({ questionType, difficulty, count }) {
      if (questionType) this.questionType = questionType
      if (difficulty) this.difficulty = difficulty
      if (typeof count === 'number') this.count = count
    },
    resetGenerated() {
      this.generatedQuestions = []
    },
    async generate(payload) {
      this.generating = true
      try {
        this.lastGeneratePayload = payload
        this.courseId = payload?.course_id || this.courseId
        const res = await generateQuestions(payload)
        if (!res?.success) {
          this.generatedQuestions = []
          return []
        }
        this.generatedQuestions = res.data || []
        return this.generatedQuestions
      } finally {
        this.generating = false
      }
    },
  },
})
