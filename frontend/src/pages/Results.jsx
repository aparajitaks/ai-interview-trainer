import React, { useEffect, useState } from 'react'
import { finishSession } from '../api/api'

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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-semibold">Interview Results</h2>
      <div className="bg-gray-800 p-4 rounded">
        <div className="text-sm text-gray-400">Total questions: {summary.total_questions}</div>
        <div className="text-lg font-bold mt-2">Average score: {(summary.average_score ?? 0).toFixed(2)}</div>
      </div>

      <div className="space-y-4">
        {answers.map((a) => (
          <div key={a.id} className="bg-gray-800 p-4 rounded">
            <div className="text-sm text-gray-300">Q id: {a.question_id}</div>
            <div className="font-medium mt-1">Score: {a.score.toFixed(2)}</div>
            <div className="text-sm mt-2 text-gray-300">Feedback: {(a.feedback || []).join('; ')}</div>
            <div className="text-sm mt-2 text-gray-300">Keywords: {(a.keywords || []).join(', ')}</div>
            <div className="text-sm mt-2 text-gray-300">Transcription: {a.answer_text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
