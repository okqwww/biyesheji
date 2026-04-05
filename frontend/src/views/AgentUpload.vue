<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'
import { uploadPdfs, workflowStart } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

const fileList = ref([])
const uploading = ref(false)

function handleChange(file, list) {
  fileList.value = list
}

function handleRemove(file, list) {
  fileList.value = list
}

function beforeUpload(file) {
  if (file.type !== 'application/pdf') {
    ElMessage.warning(`"${file.name}" 不是 PDF 文件，已忽略`)
    return false
  }
  return true
}

async function submit() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请至少上传一份往年题 PDF')
    return
  }

  uploading.value = true
  store.uploading = true

  try {
    const formData = new FormData()
    for (const f of fileList.value) {
      formData.append('files', f.raw)
    }

    const res = await uploadPdfs(formData)
    store.sessionId = res.session_id

    // 调用 LangGraph workflow：parse → analyze → interrupt
    await workflowStart(res.session_id)
    store.parsing = true

    router.push('/agent/parsing')
  } catch {
    // http.js already shows error message
  } finally {
    uploading.value = false
    store.uploading = false
  }
}
</script>

<template>
  <div class="page">
    <div class="container narrow">
      <!-- Page Header -->
      <div class="page-header animate-fade-in-up">
        <h1 class="page-heading">上传往年题 PDF</h1>
        <p class="page-desc">
          请上传一份或多份历年考试真题 PDF（含答案更佳），系统将自动解析题目结构与知识点，辅助 AI 生成今年试卷。
        </p>
      </div>

      <!-- Upload Card -->
      <div class="upload-card animate-fade-in-up" style="animation-delay: 60ms">
        <el-upload
          drag
          multiple
          accept=".pdf"
          :auto-upload="false"
          :file-list="fileList"
          :before-upload="beforeUpload"
          :on-change="handleChange"
          :on-remove="handleRemove"
          class="upload-area"
        >
          <div class="upload-content">
            <div class="upload-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                <line x1="9" y1="14" x2="15" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="upload-text">
              将 PDF 文件拖到此处，或<span class="upload-link">点击选择文件</span>
            </div>
            <div class="upload-hint">仅支持 .pdf 格式，可一次上传多份历年试题</div>
          </div>
        </el-upload>

        <div class="file-count" v-if="fileList.length > 0">
          已选择 <strong>{{ fileList.length }}</strong> 份 PDF 文件
        </div>

        <button
          class="submit-btn"
          :class="{ 'submit-btn--active': fileList.length > 0 }"
          :disabled="fileList.length === 0 || uploading"
          @click="submit"
        >
          <span v-if="uploading" class="spinner"></span>
          {{ uploading ? '上传中...' : '开始解析' }}
        </button>
      </div>

      <!-- Tips -->
      <div class="tips animate-fade-in-up" style="animation-delay: 120ms">
        <div class="tips-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
            <line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="12" y1="8" x2="12.01" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          使用提示
        </div>
        <ul>
          <li>建议上传 <strong>2–5 年</strong> 的真题，覆盖面越广，出题质量越高</li>
          <li>同时上传含参考答案的试卷，系统将自动提取答案和评分点</li>
          <li>PDF 需包含可读文字（非扫描版图片 PDF）</li>
          <li>上传后系统将调用视觉大模型精准识别，包括数学公式、表格等复杂内容</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-top: var(--space-12);
  background: var(--color-bg);
}

.container.narrow {
  max-width: 640px;
}

/* ── Page Header ─────────────────────────────── */
.page-header {
  margin-bottom: var(--space-8);
}

.page-heading {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.page-desc {
  font-size: 15px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* ── Upload Card ─────────────────────────────── */
.upload-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-8);
  margin-bottom: var(--space-5);
}

.upload-area {
  width: 100%;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-10) var(--space-6);
}

.upload-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.upload-text {
  font-size: 15px;
  color: var(--color-text);
  text-align: center;
  margin-bottom: var(--space-2);
}

.upload-link {
  color: var(--color-primary);
  cursor: pointer;
}

.upload-hint {
  font-size: 13px;
  color: var(--color-text-tertiary);
  text-align: center;
}

.file-count {
  margin-top: var(--space-5);
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.file-count strong {
  color: var(--color-primary);
}

.submit-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: var(--space-5);
  padding: 13px 24px;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border: none;
  cursor: not-allowed;
  transition: all var(--transition-base);
}

.submit-btn--active {
  background: var(--color-primary);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.submit-btn--active:hover {
  background: var(--color-primary-hover);
  box-shadow: 0 4px 16px rgba(0, 122, 255, 0.35);
  transform: translateY(-1px);
}

.submit-btn--active:active {
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

/* ── Tips ─────────────────────────────────── */
.tips {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  padding: var(--space-5) var(--space-6);
}

.tips-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-3);
}

.tips ul {
  margin: 0;
  padding: 0 0 0 var(--space-5);
  list-style: none;
}

.tips li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
  position: relative;
}

.tips li::before {
  content: '·';
  position: absolute;
  left: -14px;
  color: var(--color-text-tertiary);
}

.tips li strong {
  color: var(--color-text);
}
</style>
