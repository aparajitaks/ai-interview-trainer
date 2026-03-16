import React, { useState, useEffect } from 'react'
import CameraBox from '../components/CameraBox'
import RecordControls from '../components/RecordControls'

export default function InterviewSession() {
  const [sessionId, setSessionId] = useState(null)
  const [question, setQuestion] = useState(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [questionId, setQuestionId] = useState(null)
  const [answers, setAnswers] = useState([])
  const [busy, setBusy] = useState(false)

  const startSession = async () => {
    try {
      setBusy(true)
      const resp = await fetch('http://127.0.0.1:8000/session/start', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ role: 'candidate' }),
      })
      if (!resp.ok) {
        console.error('session start failed', resp.status)
        return
      }
      const data = await resp.json()
      setSessionId(data.session_id)
      setQuestion(data.question)
      setQuestionIndex(data.question_index)
      setQuestionId(data.question_id)
    } catch (err) {
      console.error('session start error', err)
    } finally {
      setBusy(false)
    }
  }

  const onAnalysisComplete = async (result) => {
    // result comes from RecordControls analyze upload
    try {
      if (!sessionId || !questionId) {
        console.warn('No active session/question')
        return
      }
      // extract scores; accept either final or detailed
      const score = result?.final ?? result?.result?.final_score ?? 0.0
      const emotion = result?.emotion ?? result?.result?.emotion_score ?? 0.0
      const posture = result?.posture ?? result?.result?.posture_score ?? 0.0
      const eye = result?.eye ?? result?.result?.eye_score ?? result?.result?.eye_contact_score ?? 0.0

      // save answer to session API
      const resp = await fetch('http://127.0.0.1:8000/session/answer', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question_id: questionId, score, emotion_score: emotion, posture_score: posture, eye_score: eye }),
      })
      if (!resp.ok) {
        console.error('failed to save answer', resp.status)
        return
      }
      setAnswers((a) => [...a, { questionId, score, emotion, posture, eye }])

      // fetch next question
      const nresp = await fetch('http://127.0.0.1:8000/session/next', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      if (!nresp.ok) {
        console.error('next question failed', nresp.status)
        return
      }
      const ndata = await nresp.json()
      if (ndata.done) {
        // finished session
        const fresp = await fetch('http://127.0.0.1:8000/session/finish', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        })
        const fdata = await fresp.json()
        // show final summary (simple alert for now)
        alert('Session complete. Summary: ' + JSON.stringify(fdata.summary))
        return
      }
      setQuestion(ndata.question)
      setQuestionIndex(ndata.question_index)
      setQuestionId(ndata.question_id)
    } catch (err) {
      console.error('onAnalysisComplete error', err)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-semibold mb-4">Interview Session (Advanced)</h1>
        {!sessionId ? (
          <div>
            <button onClick={startSession} disabled={busy} className="px-4 py-2 bg-indigo-600 rounded">Start Session</button>
          </div>
        ) : (
          <div>
            <div className="mb-4">
              <div className="text-sm text-slate-300">Question {questionIndex} of 5</div>
              <div className="text-lg font-medium mt-2">{question}</div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <CameraBox />
              </div>
              <div>
                <div className="p-4 bg-gray-800 rounded">
                  <div className="mb-4">Record your answer and submit to analyze.</div>
                  <RecordControls onAnalysisComplete={onAnalysisComplete} />
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="text-sm text-slate-400">Answers so far: {answers.length}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
