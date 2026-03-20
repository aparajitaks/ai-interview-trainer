import axios from 'axios'

const BASE =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL
    ? import.meta.env.VITE_API_BASE_URL
    : 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: BASE,
  timeout: 120000,
})

// Attach JWT token from localStorage if present
client.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('aiit_token')
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
  } catch (e) {
    // ignore
  }
  return config
})

export async function startSession(role) {
  const resp = await client.post('/session/start', { role: role || 'general' })
  return resp.data
}

// Legacy non-auth flow to start an interview session; returns session_id and first_question
export async function startInterview() {
  const resp = await client.post('/interview/start')
  return resp.data
}

export async function uploadAnalyze(file) {
  const fd = new FormData()
  fd.append('video', file, file.name || 'recording.webm')
  const resp = await client.post('/analyze', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return resp.data
}

export async function submitAnswer(session_id, question_id, payload) {
  const body = Object.assign({ session_id, question_id }, payload)
  const resp = await client.post('/session/answer', body)
  return resp.data
}

export async function nextQuestion(session_id) {
  const resp = await client.post('/session/next', { session_id })
  return resp.data
}

export async function finishSession(session_id) {
  const resp = await client.post('/session/finish', { session_id })
  return resp.data
}

export default client
