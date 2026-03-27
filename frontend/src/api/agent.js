import http from './http'

/**
 * 上传一或多份往年题 PDF 文件
 * @param {FormData} formData  含多个 file 字段的 FormData
 */
export function uploadPdfs(formData) {
  return http.post('/api/agent/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 触发 Agent 1 后台解析
 * @param {string} sessionId
 */
export function startParse(sessionId) {
  return http.post('/api/agent/parse', { session_id: sessionId })
}

/**
 * 轮询 Agent 1 解析结果
 * @param {string} sessionId
 */
export function getParsed(sessionId) {
  return http.get('/api/agent/parse/result', { params: { session_id: sessionId } })
}

/**
 * 触发 Agent 2 题槽分析
 * @param {string} sessionId
 */
export function startAnalyze(sessionId) {
  return http.post('/api/agent/analyze', { session_id: sessionId })
}

/**
 * 轮询 Agent 2 题槽分析结果
 * @param {string} sessionId
 */
export function getAnalyzed(sessionId) {
  return http.get('/api/agent/analyze/result', { params: { session_id: sessionId } })
}

/**
 * 触发 Agent 4 并行题目生成
 * @param {string} sessionId
 * @param {string} level  "small" | "medium" | "large"
 * @param {Array|null} slotTemplate  教师编辑后的题槽列表，null 则使用 session 中已有的
 */
export function startGenerate(sessionId, level = 'medium', slotTemplate = null) {
  const body = { session_id: sessionId, modification_level: level }
  if (slotTemplate !== null) body.slot_template = slotTemplate
  return http.post('/api/agent/generate', body)
}

/**
 * 轮询 Agent 4 题目生成结果
 * @param {string} sessionId
 */
export function getGenerated(sessionId) {
  return http.get('/api/agent/generate/result', { params: { session_id: sessionId } })
}

/**
 * 单题反馈重新生成
 * @param {string} sessionId
 * @param {number} slotId
 * @param {string} message  教师反馈文字
 */
export function regenerate(sessionId, slotId, message) {
  return http.post('/api/agent/regenerate', {
    session_id: sessionId,
    slot_id: slotId,
    message,
  })
}

/**
 * 触发 Agent 1.5 知识图谱提取
 * @param {string} sessionId
 */
export function startKg(sessionId) {
  return http.post('/api/agent/kg/start', { session_id: sessionId })
}

/**
 * 轮询 Agent 1.5 知识图谱提取结果
 * @param {string} sessionId
 */
export function getKg(sessionId) {
  return http.get('/api/agent/kg/result', { params: { session_id: sessionId } })
}
