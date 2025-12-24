import http from './http'

export function getCourses() {
  return http.get('/api/courses')
}
