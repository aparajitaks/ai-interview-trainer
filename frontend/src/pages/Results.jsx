import React, { useEffect, useState } from 'react'
import { finishSession } from '../api/api'
import { motion } from 'framer-motion'

export default function Results() {
  const [summary, setSummary] = useState(null)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const sid = sessionStorage.getItem('aiit_session_id')
    if (!sid) {
      setLoading(false)
      return
    }
    ;(async () => {
      try {
        const res = await finishSession(sid)
        setSummary(res.summary || res)
        setAnswers(res.answers || [])
      } catch (err) {
        console.error('failed to fetch results', err)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="text-gray-300">Loading results...</div>
  if (!summary) return <div className="text-gray-300">No results available</div>

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
            <div className="text-xl font-semibold">{summary.total_questions}</div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Average Score</div>
            <div className="text-3xl font-bold mt-2">{((summary.average_score ?? 0) * 100).toFixed(0)}%</div>
            <div className="mt-4 h-3 bg-gray-700 rounded-full overflow-hidden">
              <div className={`${scoreColor(summary.average_score ?? 0)} h-3`} style={{ width: `${Math.min(100, Math.max(0, (summary.average_score ?? 0) * 100))}%` }} />
            </div>
          </motion.div>

          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Top Strength</div>
            <div className="text-lg font-semibold mt-2">Review detailed feedback per question below</div>
          </motion.div>

          <motion.div className="p-6 rounded-2xl bg-gray-800 shadow-lg" whileHover={{ y: -4 }}>
            <div className="text-sm text-gray-300">Next Steps</div>
            <div className="text-lg font-semibold mt-2">Practice more role-specific questions to improve scores</div>
          </motion.div>
        </div>

        <div className="space-y-4">
          {answers.map((a) => (
            <motion.div key={a.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-800 p-6 rounded-2xl shadow-lg">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-400">Q id: {a.question_id}</div>
                  <div className="text-2xl font-semibold mt-1">Score: {(a.score ?? 0).toFixed(2)}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-400">Emotion</div>
                  <div className="font-medium">{((a.emotion_score ?? 0) * 100).toFixed(0)}%</div>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Emotion</div>
                  <div className="font-semibold">{((a.emotion_score ?? 0) * 100).toFixed(0)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.emotion_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.emotion_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Posture</div>
                  <div className="font-semibold">{((a.posture_score ?? 0) * 100).toFixed(0)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.posture_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.posture_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Eye Contact</div>
                  <div className="font-semibold">{((a.eye_score ?? 0) * 100).toFixed(0)}%</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-2 ${scoreColor(a.eye_score ?? 0)}`} style={{ width: `${Math.min(100, Math.max(0, (a.eye_score ?? 0) * 100))}%` }} />
                  </div>
                </div>

                <div className="p-3 bg-gray-900 rounded">
                  <div className="text-sm text-gray-400">Final Rating</div>
                  <div className="font-semibold">{(a.feedback?.final_rating ?? ((a.score ?? 0) * 5)).toFixed ? (a.feedback?.final_rating ?? ((a.score ?? 0) * 5)).toFixed(2) : ((a.feedback?.final_rating ?? ((a.score ?? 0) * 5)) + '')}</div>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Strengths</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.strengths || []).map((s, i) => (<li key={i}>{s}</li>))}
                    {!(a.feedback?.strengths || []).length && <li className="text-gray-400">No strengths detected</li>}
                  </ul>
                </div>

                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Weaknesses</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.weaknesses || []).map((s, i) => (<li key={i}>{s}</li>))}
                    {!(a.feedback?.weaknesses || []).length && <li className="text-gray-400">No weaknesses provided</li>}
                  </ul>
                </div>

                <div className="p-4 bg-gray-900 rounded">
                  <div className="text-sm text-gray-300 mb-2">Suggestions</div>
                  <ul className="list-disc pl-5 text-gray-200">
                    {(a.feedback?.suggestions || []).map((s, i) => (<li key={i}>{s}</li>))}
                    {!(a.feedback?.suggestions || []).length && <li className="text-gray-400">No suggestions</li>}
                  </ul>
                </div>
              </div>

              <div className="mt-4 text-sm text-gray-400">Keywords: {(a.keywords || []).join(', ')}</div>
              <div className="mt-1 text-sm text-gray-400">Transcription: {a.answer_text}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
