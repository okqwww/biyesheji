import http from './http'

export function getCourseGraph(courseId) {
  return http.get(`/api/courses/${courseId}/graph`)
}
