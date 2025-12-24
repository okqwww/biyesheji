import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  timeout: 70000,
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const data = error?.response?.data

    let message = '请求失败'
    if (typeof data?.detail === 'string') message = data.detail
    else if (data?.detail?.message) message = data.detail.message
    else if (typeof data?.message === 'string') message = data.message
    else if (error?.message) message = error.message

    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default http
