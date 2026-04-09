/**
 * api.js
 * ------
 * Thin service layer for all FastAPI backend calls.
 * All network details are centralised here so components stay clean.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * POST /analyze-video
 * Sends a video file as multipart/form-data and returns the analysis result.
 *
 * @param {File}     file       - The video file selected by the user.
 * @param {Function} onProgress - Optional callback(percent) for upload progress.
 * @returns {Promise<AnalysisResult>}
 * @throws {Error} with a human-readable message on HTTP or network failure.
 */
export async function analyzeVideo(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  // Use XMLHttpRequest instead of fetch so we get upload-progress events.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Received an invalid response from the server.'))
        }
      } else {
        // Try to extract FastAPI's detail field
        let detail = `Request failed (HTTP ${xhr.status})`
        try {
          const body = JSON.parse(xhr.responseText)
          if (body.detail) detail = body.detail
        } catch { /* ignore */ }
        reject(new Error(detail))
      }
    })

    xhr.addEventListener('error', () =>
      reject(new Error('Network error — is the API server running on port 8000?'))
    )
    xhr.addEventListener('timeout', () =>
      reject(new Error('Request timed out. The video may be too long.'))
    )

    xhr.timeout = 5 * 60 * 1000  // 5 min max
    xhr.open('POST', `${API_BASE}/analyze-video`)
    xhr.send(formData)
  })
}

/**
 * GET /health — liveness check.
 * @returns {Promise<{status: string, pipeline_ready: boolean}>}
 */
export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}
