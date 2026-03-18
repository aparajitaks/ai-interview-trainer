import axios from 'axios'

const BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: BASE,
  timeout: 120000,
})

export async function startSession(role) {
  const resp = await client.post('/session/start', { role })
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
