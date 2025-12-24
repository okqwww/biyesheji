import { defineStore } from 'pinia'
import { getCourses } from '../api/courses'
import { getCourseGraph } from '../api/graph'

export const useCourseStore = defineStore('course', {
  state: () => ({
    courses: [],
    loadingCourses: false,
    currentCourseId: null,
    graphNodes: [],
    graphEdges: [],
    loadingGraph: false,
  }),
  getters: {
    currentCourse(state) {
      return state.courses.find((c) => c.id === state.currentCourseId) || null
    },
  },
  actions: {
    async fetchCourses() {
      if (this.loadingCourses) return
      this.loadingCourses = true
      try {
        const res = await getCourses()
        if (res?.success) this.courses = res.data || []
        else this.courses = []
      } finally {
        this.loadingCourses = false
      }
    },
    async fetchCourseGraph(courseId) {
      if (!courseId) return
      this.currentCourseId = courseId
      this.loadingGraph = true
      try {
        const res = await getCourseGraph(courseId)
        if (res?.success && res?.data) {
          this.graphNodes = res.data.nodes || []
          this.graphEdges = res.data.edges || []
        } else {
          this.graphNodes = []
          this.graphEdges = []
        }
      } finally {
        this.loadingGraph = false
      }
    },
  },
})
