import React, { useState, useCallback } from 'react'
import CameraBox from '../components/CameraBox'
import RecordControls from '../components/RecordControls'

export default function InterviewSession() {
  const [sessionId, setSessionId] = useState(null)
  const [question, setQuestion] = useState(null)
  const [questionIndex, setQuestionIndex] = useState(null)
  const [questionId, setQuestionId] = useState(null)
  const [stream, setStream] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('idle')
  const [answers, setAnswers] = useState([])
  const [busy, setBusy] = useState(false)

  const startSession = async () => {
    if (loading || busy || sessionId) return
    setBusy(true)
    setLoading(true)
    setStatus('starting')
    console.log('session start')
    try {
      let resp
      try {
        resp = await fetch('http://127.0.0.1:8000/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
      } catch (err) {
        console.error('session start fetch failed', err)
        setStatus('error')
        alert('Failed to start session (network)')
        return
      }

      if (!resp.ok) {
        const txt = await resp.text().catch(() => '')
        setStatus('error')
        console.error('start session failed', resp.status, txt)
        alert('Failed to start session')
        return
      }

      let data = null
      try {
        data = await resp.json()
      } catch (err) {
        console.error('failed to parse session start response', err)
        setStatus('error')
        alert('Failed to start session (bad response)')
        return
      }

      setSessionId(data.session_id)
      setQuestion(data.question)
      setQuestionIndex(data.question_index ?? data.questionIndex ?? null)
      setQuestionId(data.question_id ?? data.questionId ?? null)
      setStatus('ready')
      console.log('question loaded', data.question, 'index', data.question_index ?? data.questionIndex)
    } catch (err) {
      console.error('start session error', err)
      setStatus('error')
      alert('Failed to start session')
    } finally {
      setLoading(false)
      setBusy(false)
    }
  }

  const onStreamAvailable = useCallback((s) => {
    setStream(s)
  }, [])

  // onAnalysisComplete receives the JSON returned by /analyze (or error)
  const onAnalysisComplete = async (data) => {
    // prevent re-entrancy
    if (busy) {
      console.warn('onAnalysisComplete called while busy')
      return
    }
    setBusy(true)
    // ensure parent UI state
    setLoading(false)
    if (!sessionId) {
      console.warn('no session; ignoring analysis result')
      setBusy(false)
      return
    }

    console.log('record done')

    if (data && data.error) {
      setStatus('error')
      alert('Analysis failed: ' + data.error)
      return
    }

    // the /analyze endpoint returns either { result: {...} , session_id } or the raw result
    const analysis = (data && data.result) ? data.result : data || {}

    // map various possible field names to the answer API contract
    const score = parseFloat(analysis.final_score ?? analysis.score ?? 0.0) || 0.0
    const emotion_score = parseFloat(analysis.emotion_score ?? analysis.emotion ?? 0.0) || 0.0
    const posture_score = parseFloat(analysis.posture_score ?? analysis.posture ?? 0.0) || 0.0
    const eye_score = parseFloat(analysis.eye_score ?? analysis.eye_contact_score ?? 0.0) || 0.0

    // persist the answer to session API
    try {
      setStatus('saving')
      const payload = {
        session_id: sessionId,
        question_id: questionId,
        score,
        emotion_score,
        posture_score,
        eye_score,
      }

      let resp
      try {
        resp = await fetch('http://127.0.0.1:8000/session/answer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (err) {
        console.error('save answer fetch failed', err)
        setStatus('error')
        alert('Failed to save answer (network)')
        setBusy(false)
        return
      }

      if (!resp.ok) {
        const txt = await resp.text().catch(() => '')
        console.error('failed to save answer', resp.status, txt)
        setStatus('error')
        alert('Failed to save answer')
        setBusy(false)
        return
      }

      console.log('answer saved')
      // add to local answers list for UI
      setAnswers((a) => [...a, { questionIndex, questionId, score, emotion_score, posture_score, eye_score }])

      // request next question
      setStatus('fetching_next')
      let nxt
      try {
        nxt = await fetch('http://127.0.0.1:8000/session/next', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        })
      } catch (err) {
        console.error('next question fetch failed', err)
        setStatus('error')
        alert('Failed to get next question (network)')
        setBusy(false)
        return
      }

      if (!nxt.ok) {
        const txt = await nxt.text().catch(() => '')
        console.error('failed to get next question', nxt.status, txt)
        setStatus('error')
        alert('Failed to get next question')
        setBusy(false)
        return
      }

      let nextData = null
      try {
        nextData = await nxt.json()
      } catch (err) {
        console.error('failed to parse next question response', err)
        setStatus('error')
        alert('Failed to get next question (bad response)')
        setBusy(false)
        return
      }

      console.log('next question')
      if (nextData.done) {
        // finish session
        setStatus('finishing')
        let fin
        try {
          fin = await fetch('http://127.0.0.1:8000/session/finish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId }),
          })
        } catch (err) {
          console.error('finish session fetch failed', err)
          setStatus('error')
          alert('Failed to finish session (network)')
          setBusy(false)
          return
        }

        if (fin.ok) {
          const finData = await fin.json().catch(() => null)
          setStatus('done')
          console.log('session finished')
          alert('Session finished: ' + JSON.stringify(finData?.summary || finData || {}))
        } else {
          const txt = await fin.text().catch(() => '')
          console.error('failed to finish session', fin.status, txt)
          setStatus('error')
          alert('Failed to finish session')
        }
        setBusy(false)
        return
      }

      // otherwise set next question (support both snake_case and camelCase)
      setQuestion(nextData.question)
      setQuestionIndex(nextData.question_index ?? nextData.questionIndex ?? null)
      setQuestionId(nextData.question_id ?? nextData.questionId ?? null)
      setStatus('ready')
      setBusy(false)
    } catch (err) {
      console.error('onAnalysisComplete error', err)
      setStatus('error')
      alert('Internal error saving answer or fetching next')
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Interview Session</h2>
        <div>
          {!sessionId ? (
            <button onClick={startSession} className="px-4 py-2 bg-indigo-600 rounded hover:bg-indigo-500">Start Session</button>
          ) : (
            <span className="text-sm text-gray-400">Session: {sessionId}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="col-span-2">
          <div className="mb-4">
            <div className="text-lg font-medium">Question {questionIndex ?? '-'}</div>
            <div className="mt-2 text-gray-200 text-xl">{question ?? 'Press "Start Session" to begin.'}</div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4">
            <CameraBox onStreamAvailable={onStreamAvailable} />
            <div className="mt-4 flex items-center justify-center">
              <RecordControls
                stream={stream}
                onAnalysisComplete={onAnalysisComplete}
                setLoading={setLoading}
                setStatus={setStatus}
              />
            </div>
            <div className="mt-3 text-sm text-gray-400">Status: {status}</div>
          </div>
        </div>

        <aside className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-2">Answers</h3>
          {answers.length === 0 ? (
            <div className="text-sm text-gray-400">No answers yet</div>
          ) : (
            <ul className="space-y-2 text-sm">
              {answers.map((a, idx) => (
                <li key={idx} className="p-2 bg-gray-900 rounded">
                  Q{a.questionIndex} — score: {a.score.toFixed(2)} (emotion {a.emotion_score.toFixed(2)}, posture {a.posture_score.toFixed(2)}, eye {a.eye_score.toFixed(2)})
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  )
}
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
