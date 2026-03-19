import React, { useState, useCallback, useEffect } from 'react'
import CameraBox from '../components/CameraBox'
import RecordControls from '../components/RecordControls'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { startSession as apiStart, submitAnswer, nextQuestion, finishSession } from '../api/api'

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
  const [timer, setTimer] = useState(60)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const sid = sessionStorage.getItem('aiit_session_id')
    const q = sessionStorage.getItem('aiit_question')
    const qid = sessionStorage.getItem('aiit_question_id')
    if (sid) setSessionId(sid)
    if (q) setQuestion(q)
    if (qid) setQuestionId(qid)
  }, [])

  const startSession = async () => {
    if (loading || busy || sessionId) return
    setBusy(true)
    setLoading(true)
    setStatus('starting')
    setError('')
    try {
      const data = await apiStart()
      setSessionId(data.session_id)
      setQuestion(data.question)
      setQuestionIndex(data.question_index ?? null)
      setQuestionId(data.question_id ?? null)
      setStatus('ready')
    } catch (err) {
      console.error('start session error', err)
      setStatus('error')
      setError('Failed to start session. Check your network or backend and try again.')
    } finally {
      setLoading(false)
      setBusy(false)
    }
  }

  const onStreamAvailable = useCallback((s) => setStream(s), [])

  useEffect(() => {
    let t = null
    if (busy) {
      setTimer(60)
      t = setInterval(() => setTimer((v) => Math.max(0, v - 1)), 1000)
    } else setTimer(60)
    return () => t && clearInterval(t)
  }, [busy])

  const onAnalysisComplete = async (data) => {
    if (busy) return
    setBusy(true)
    setLoading(false)
    setError('')
    if (!sessionId) {
      setError('No active session. Please start a session first.')
      setBusy(false)
      return
    }

    try {
      const analysis = (data && data.result) ? data.result : data || {}
      const score = parseFloat(analysis.final_score ?? analysis.score ?? 0.0) || 0.0
      const emotion_score = parseFloat(analysis.emotion_score ?? analysis.emotion ?? 0.0) || 0.0
      const posture_score = parseFloat(analysis.posture_score ?? analysis.posture ?? 0.0) || 0.0
      const eye_score = parseFloat(analysis.eye_score ?? analysis.eye_contact_score ?? 0.0) || 0.0

      const payload = { score, emotion_score, posture_score, eye_score }
      // submit answer via API helper
      await submitAnswer(sessionId, questionId, payload)

      setAnswers((a) => [...a, { questionIndex, questionId, score, emotion_score, posture_score, eye_score }])

      // request next question
      const nextData = await nextQuestion(sessionId)
      if (nextData.done) {
        await finishSession(sessionId)
        navigate('/results')
        setBusy(false)
        return
      }

      setQuestion(nextData.question)
      setQuestionIndex(nextData.question_index ?? null)
      setQuestionId(nextData.question_id ?? null)
      setStatus('ready')
    } catch (err) {
      console.error('onAnalysisComplete error', err)
      setStatus('error')
      setError('Failed saving or fetching next question. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const last = answers.length ? answers[answers.length - 1] : null

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 p-8 text-white">
      <div className="max-w-6xl mx-auto">
        <header className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold">Interview Session</h2>
          <div>
            {!sessionId ? (
              <button onClick={startSession} disabled={busy || loading} className="px-4 py-2 bg-indigo-600 rounded-2xl shadow-lg hover:bg-indigo-500 disabled:opacity-60">{loading ? 'Starting...' : 'Start Session'}</button>
            ) : (
              <span className="text-sm text-gray-300">Session: {sessionId}</span>
            )}
          </div>
        </header>

        {error && <div className="mb-4 p-3 rounded-md bg-red-700 text-red-100">{error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <motion.section className="col-span-2 bg-gray-800 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400">Question {questionIndex ?? '-'}</div>
                <motion.div key={question} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-2 text-xl font-semibold text-white">
                  {question ?? 'Press "Start Session" to begin.'}
                </motion.div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-400">Timer</div>
                <div className="text-xl font-semibold">{timer}s</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-900 rounded-2xl p-4">
                <CameraBox onStreamAvailable={onStreamAvailable} />
              </div>

              <div className="flex flex-col space-y-4">
                <div className="p-4 bg-gray-900 rounded-2xl">
                  <div className="text-sm text-gray-400 mb-2">Record</div>
                  <RecordControls
                    stream={stream}
                    onAnalysisComplete={onAnalysisComplete}
                    setLoading={setLoading}
                    setStatus={setStatus}
                  />
                </div>

                <div className="p-4 bg-gray-900 rounded-2xl">
                  <div className="text-sm text-gray-400">Status</div>
                  <div className="font-medium mt-1">{status}</div>
                </div>
              </div>
            </div>

            <div className="mt-4">
              <h3 className="text-lg font-semibold">Answers</h3>
              <div className="mt-2 space-y-2">
                {answers.length === 0 ? (
                  <div className="text-sm text-gray-400">No answers yet</div>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {answers.map((a, idx) => (
                      <li key={idx} className="p-2 bg-gray-900 rounded">Q{a.questionIndex} — score: {Number(a.score ?? 0).toFixed(2)} (emotion {Number(a.emotion_score ?? 0).toFixed(2)}, posture {Number(a.posture_score ?? 0).toFixed(2)}, eye {Number(a.eye_score ?? 0).toFixed(2)})</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </motion.section>

          <aside className="bg-gray-800 p-6 rounded-2xl shadow-lg order-first lg:order-last">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-lg font-semibold">Live Score</h4>
                <div className="text-sm text-gray-400">Real-time feedback on your last answer</div>
              </div>
            </div>

            <div className="mt-2 space-y-3">
              <div className="p-3 bg-gray-900 rounded">
                <div className="text-sm text-gray-400">Final Score</div>
                <div className="text-2xl font-bold">{last ? Number(last.score ?? 0).toFixed(2) : '-'}</div>
              </div>

              <div className="p-3 bg-gray-900 rounded">
                <div className="text-sm text-gray-400">Emotion</div>
                <div className="font-medium">{last ? `${Math.round((last.emotion_score ?? 0) * 100)}%` : '-'}</div>
              </div>

              <div className="p-3 bg-gray-900 rounded">
                <div className="text-sm text-gray-400">Posture</div>
                <div className="font-medium">{last ? `${Math.round((last.posture_score ?? 0) * 100)}%` : '-'}</div>
              </div>

              <div className="p-3 bg-gray-900 rounded">
                <div className="text-sm text-gray-400">Eye Contact</div>
                <div className="font-medium">{last ? `${Math.round((last.eye_score ?? 0) * 100)}%` : '-'}</div>
              </div>
            </div>
          </aside>
        </div>

        {/* global busy overlay */}
        {(loading || busy) && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
            <div className="bg-gray-800 p-6 rounded-lg shadow-lg flex items-center space-x-4">
              <svg className="animate-spin h-6 w-6 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
              </svg>
              <div className="text-white">{loading ? 'Preparing session...' : 'Processing answer...'}</div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
