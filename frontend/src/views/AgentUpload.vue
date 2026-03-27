<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useAgentStore } from '../stores/agent'
import { uploadPdfs, startParse } from '../api/agent'

const router = useRouter()
const store = useAgentStore()

const fileList = ref([])
const uploading = ref(false)

/** el-upload 只收集文件，不自动上传 */
function handleChange(file, list) {
  fileList.value = list
}

function handleRemove(file, list) {
  fileList.value = list
}

/** 校验：只允许 PDF */
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

    await startParse(res.session_id)
    store.parsing = true

    router.push('/agent/parsing')
  } catch {
    // http.js 已弹出错误提示
  } finally {
    uploading.value = false
    store.uploading = false
  }
}
</script>

<template>
  <div class="page">
    <div class="container narrow">
      <div class="header">
        <div class="breadcrumb">
          <el-button text @click="$router.push('/')">← 返回首页</el-button>
        </div>
        <h1 class="page-title">上传往年题 PDF</h1>
        <p class="page-desc">
          请上传一份或多份历年考试真题 PDF（含答案更佳），系统将自动解析题目结构与知识点，辅助 AI 生成今年试卷。
        </p>
      </div>

      <div class="upload-card glass">
        <el-upload
          drag
          multiple
          accept=".pdf"
          :auto-upload="false"
          :file-list="fileList"
          :before-upload="beforeUpload"
          :on-change="handleChange"
          :on-remove="handleRemove"
          class="upload-dragger"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            将 PDF 文件拖到此处，或
            <span class="upload-link">点击选择文件</span>
          </div>
          <div class="upload-hint">仅支持 .pdf 格式，可一次上传多份历年试题</div>
        </el-upload>

        <div class="file-count" v-if="fileList.length > 0">
          已选择 <strong>{{ fileList.length }}</strong> 份 PDF 文件
        </div>

        <div class="actions">
          <el-button
            type="primary"
            size="large"
            :loading="uploading"
            :disabled="fileList.length === 0"
            @click="submit"
          >
            {{ uploading ? '上传中...' : '开始解析' }}
          </el-button>
        </div>
      </div>

      <div class="tips glass">
        <div class="tips-title">使用提示</div>
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
.narrow {
  max-width: 720px;
}

.header {
  margin-bottom: 28px;
}

.breadcrumb {
  margin-bottom: 12px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
}

.page-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.upload-card {
  padding: 32px;
  border-radius: 16px;
  margin-bottom: 20px;
}

.upload-dragger :deep(.el-upload-dragger) {
  background: rgba(255, 255, 255, 0.04);
  border: 1.5px dashed rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  padding: 40px 20px;
  transition: border-color 0.2s;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: rgba(99, 102, 241, 0.7);
}

.upload-icon {
  font-size: 48px;
  color: rgba(99, 102, 241, 0.8);
  margin-bottom: 12px;
}

.upload-text {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 6px;
}

.upload-link {
  color: #818cf8;
  cursor: pointer;
}

.upload-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.file-count {
  margin-top: 16px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.tips {
  padding: 20px 24px;
  border-radius: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.tips-title {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 10px;
}

.tips ul {
  margin: 0;
  padding-left: 18px;
  line-height: 2;
}

.tips li strong {
  color: rgba(255, 255, 255, 0.9);
}
</style>
