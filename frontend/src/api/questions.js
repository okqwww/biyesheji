import http from './http'

export function generateQuestions(payload) {
  return http.post('/api/questions/generate', payload)
}

export function saveQuestions(payload) {
  return http.post('/api/questions/save', payload)
}

export function updateQuestion(questionId, payload) {
  return http.put(`/api/questions/${questionId}`, payload)
}

export function exportMarkdown(questions) {
  return http.post('/api/questions/export/markdown', questions, { responseType: 'text' })
}
