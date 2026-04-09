/**
 * interviewApi.js
 * ---------------
 * All network calls for the live interview system.
 * Completely separate from api.js (video analysis) — easy to swap backends.
 */

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function apiCall(path, options) {
  const url = `${API}${path}`
  console.log('Calling API:', url)
  try {
    return await fetch(url, options)
  } catch (err) {
    console.error('API ERROR:', err)
    throw err
  }
}

async function parseError(res, fallbackMessage) {
  const err = await res.json().catch(() => ({}))
  throw new Error(err.detail ?? fallbackMessage)
}

async function requestWithFallbacks({ candidates, options, errorMessage }) {
  let lastStatus = null
  for (const path of candidates) {
    const res = await apiCall(path, options)
    if (res.ok) return res.json()
    lastStatus = res.status
    // Try next candidate only when route is missing.
    if (res.status !== 404) {
      await parseError(res, `${errorMessage} (${res.status})`)
    }
  }
  throw new Error(`${errorMessage}${lastStatus ? ` (${lastStatus})` : ''}`)
}

/**
 * Start a new interview session.
 * @param {object} opts
 * @param {string} opts.role       - Job title, e.g. "AI Engineer"
 * @param {number} opts.maxRounds  - Number of Q&A rounds (default 5)
 * @returns {Promise<{session_id, question, round_number, total_rounds}>}
 */
export async function startInterview({ role, maxRounds = 5 }) {
  return requestWithFallbacks({
    candidates: ['/start-interview', '/interview/start'],
    options: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, max_rounds: maxRounds }),
    },
    errorMessage: 'Failed to start interview',
  })
}

/**
 * Submit a recorded audio answer.
 * @param {object} opts
 * @param {string} opts.sessionId  - Session ID from startInterview
 * @param {Blob}   opts.audioBlob  - Recording from MediaRecorder
 * @returns {Promise<{transcript, feedback, score, next_question, is_complete, round_number, total_rounds}>}
 */
export async function submitAnswer({ sessionId, audioBlob }) {
  const fd = new FormData()
  fd.append('session_id', sessionId)
  if (audioBlob) {
    fd.append('audio', audioBlob, 'recording.webm')
  }

  return requestWithFallbacks({
    candidates: ['/submit-answer', '/interview/submit-answer'],
    options: {
      method: 'POST',
      body: fd,
    },
    errorMessage: 'Failed to submit answer',
  })
}

export async function submitCodeAnswer({ sessionId, answer }) {
  return requestWithFallbacks({
    candidates: ['/submit-answer', '/interview/submit-answer'],
    options: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, answer }),
    },
    errorMessage: 'Failed to submit answer',
  })
}

export async function runCode({ code, input = '' }) {
  return requestWithFallbacks({
    candidates: ['/run-code'],
    options: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, input }),
    },
    errorMessage: 'Failed to run code',
  })
}

/**
 * Text-first V5 endpoint: evaluate answer and get next question.
 * Useful for typed interviews and testing dynamic flow without audio.
 */
export async function aiNextQuestion({ sessionId, question, answer, domain }) {
  return requestWithFallbacks({
    candidates: ['/ai-next-question', '/next-question'],
    options: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question,
        answer,
        domain,
      }),
    },
    errorMessage: 'Failed to generate next question',
  })
}

/**
 * Skip the current question (user click or inactivity timer).
 * @param {string} sessionId
 * @returns {Promise<{skipped, next_question, is_complete, round_number, total_rounds}>}
 */
export async function skipQuestion(sessionId) {
  const fd = new FormData()
  fd.append('session_id', sessionId)

  return requestWithFallbacks({
    candidates: ['/interview/skip-question'],
    options: {
      method: 'POST',
      body: fd,
    },
    errorMessage: 'Failed to skip question',
  })
}

/**
 * End the session (user exits early or all rounds done).
 * @param {string} sessionId
 * @returns {Promise<FinalFeedback>}
 */
export async function endInterview(sessionId) {
  const fd = new FormData()
  fd.append('session_id', sessionId)

  return requestWithFallbacks({
    candidates: ['/end-interview', '/interview/end'],
    options: {
      method: 'POST',
      body: fd,
    },
    errorMessage: 'Failed to end interview',
  })
}

