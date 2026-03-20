import React, { useEffect, useState } from 'react'
import { finishSession } from '../api/api'
import { motion } from 'framer-motion'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'

export default function Results() {
  const [summary, setSummary] = useState(null)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const sid = sessionStorage.getItem('aiit_session_id')
    if (!sid) {
      setLoading(false)
      return
    }
    ;(async () => {
      try {
        // Prefer the new session detail endpoint which provides per-question breakdown
        const detailResp = await fetch(`http://127.0.0.1:8000/session/${sid}`)
        if (detailResp.ok) {
          const detail = await detailResp.json().catch(() => null)
          if (detail) {
            setSummary(detail.summary || detail)
            setAnswers(detail.answers || detail.answers_list || detail.answers || [])
            return
          }
        }

        // Fallback to calling finishSession if the GET detail is not available
        const res = await finishSession(sid)
        setSummary(res.summary || res)
        setAnswers(res.answers || [])
      } catch (err) {
        console.error('failed to fetch results', err)
        setError('Unable to fetch results. Please try again later.')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 p-8 text-white">
      <div className="flex items-center space-x-3">
        <svg className="animate-spin h-6 w-6 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
        </svg>
        <div className="text-gray-200">Loading results...</div>
      </div>
    </div>
  )

  if (error) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 p-8 text-white">
      <div className="bg-red-700 p-4 rounded">{error}</div>
    </div>
  )

  if (!summary) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 p-8 text-white">
      <div className="text-gray-300">No results available</div>
    </div>
  )

  const scoreColor = (v) => {
    if (v >= 0.75) return 'bg-green-500'
    if (v >= 0.5) return 'bg-yellow-400'
    return 'bg-red-500'
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 p-8 text-white">
      <div className="max-w-5xl mx-auto">
        <header className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold">Interview Results</h2>
          <div className="text-right">
            <div className="text-sm text-gray-300">Total questions</div>
            <div className="text-xl font-semibold">{summary.total_questions ?? 0}</div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Average Score</div>
            <div className="text-3xl font-bold mt-2">{Math.round(((summary.average_score ?? 0) * 100))}%</div>
            <div className="mt-4 h-3 bg-gray-700 rounded-full overflow-hidden">
              <div className={`${scoreColor(summary.average_score ?? 0)} h-3`} style={{ width: `${Math.min(100, Math.max(0, (summary.average_score ?? 0) * 100))}%` }} />
            </div>
          </motion.div>

          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Top Strength</div>
            <div className="text-lg font-semibold mt-2">{summary.top_strength ?? 'Review detailed feedback below'}</div>
          </motion.div>

          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Next Steps</div>
            <div className="text-lg font-semibold mt-2">Practice more role-specific questions to improve scores</div>
          </motion.div>
        </div>

        {/* quick per-question scores chart */}
        <div className="mb-6 p-6 rounded-2xl bg-gray-800 shadow-lg">
          <div className="text-sm text-gray-300 mb-4">Per-question scores</div>
          {answers.length === 0 ? (
            <div className="text-gray-400">No per-question data available for chart.</div>
          ) : (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={answers.map((a, i) => ({
                  name: `Q${i + 1}`,
                  score: Number(a.score ?? 0) * 100,
                  emotion: Number(a.emotion_score ?? 0) * 100,
                  posture: Number(a.posture_score ?? 0) * 100,
                  eye: Number(a.eye_score ?? 0) * 100,
                }))}>
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="score" fill="#10b981" />
                  <Bar dataKey="emotion" fill="#60a5fa" />
                  <Bar dataKey="posture" fill="#f59e0b" />
                  <Bar dataKey="eye" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="space-y-4">
          {answers.length === 0 && <div className="text-gray-400">No per-question answers were returned.</div>}
          {answers.map((a) => (
            <motion.div key={a.id || `${a.question_id}-${Math.random()}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-800 p-6 rounded-2xl shadow-lg">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-400">Q id: {a.question_id}</div>
                  <div className="text-2xl font-semibold mt-1">Score: {(Number(a.score ?? 0)).toFixed(2)}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-400">Emotion</div>
                  <div className="font-medium">{Math.round((a.emotion_score ?? 0) * 100)}%</div>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Emotion</div>
                  <div className="font-semibold">{Math.round((a.emotion_score ?? 0) * 100)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.emotion_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.emotion_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Posture</div>
                  <div className="font-semibold">{Math.round((a.posture_score ?? 0) * 100)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.posture_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.posture_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Eye Contact</div>
                  <div className="font-semibold">{Math.round((a.eye_score ?? 0) * 100)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.eye_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.eye_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Final Rating</div>
                  <div className="font-semibold">{a.feedback?.final_rating ?? (Number(a.score ?? 0) * 5).toFixed ? (Number(a.feedback?.final_rating ?? (Number(a.score ?? 0) * 5))).toFixed(2) : ((a.feedback?.final_rating ?? ((a.score ?? 0) * 5)) + '')}</div>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Strengths</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.strengths || []).length ? (a.feedback.strengths.map((s, i) => (<li key={i}>{s}</li>))) : <li className="text-gray-400">No strengths detected</li>}
                  </ul>
                </div>

                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Weaknesses</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.weaknesses || []).length ? (a.feedback.weaknesses.map((s, i) => (<li key={i}>{s}</li>))) : <li className="text-gray-400">No weaknesses provided</li>}
                  </ul>
                </div>

                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Suggestions</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.suggestions || []).length ? (a.feedback.suggestions.map((s, i) => (<li key={i}>{s}</li>))) : <li className="text-gray-400">No suggestions</li>}
                  </ul>
                </div>
              </div>

              <div className="mt-4 text-sm text-gray-400">Keywords: {(a.keywords || []).join(', ')}</div>
              <div className="mt-1 text-sm text-gray-400">Transcription: {a.answer_text || '—'}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
