import React from 'react'
import { useNavigate } from 'react-router-dom'
import ScoreCard from '../components/ScoreCard'

export default function Result({ result }) {
  // Normalize result shape from /analyze: may be {result: {...}} or flat scores
  const normalized = (() => {
    if (!result) return null
    if (result.result && typeof result.result === 'object') return result.result
    return result
  })()

  const data = normalized || {
    emotion: 0,
    eye: 0,
    posture: 0,
    final: 0,
    feedback: [],
  }

  // normalize percentage-like values: accept either 0..1 or 0..100 inputs
  const pct = (v) => {
    const val = v ?? 0
    if (val > 1) return Math.round(val)
    return Math.round(val * 100)
  }

  if (result && result.error) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-full max-w-2xl px-6">
          <div className="bg-red-900/30 border border-red-800 rounded-2xl p-8 shadow-md text-center">
            <h2 className="text-2xl font-semibold mb-2">Analysis failed</h2>
            <p className="text-sm text-red-200 mb-4">{String(result.error || 'An unknown error occurred during analysis.')}</p>
            <div>
              <button onClick={() => window.history.back()} className="px-4 py-2 rounded bg-white/6 text-white">Back</button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="w-full max-w-4xl px-6">
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-8 shadow-xl">
          <div className="text-center">
            <h1 className="text-3xl font-semibold mb-6">Interview Results</h1>
          </div>

          <div className="flex flex-col md:flex-row items-center md:items-start md:space-x-8">
            {/* Final score big card */}
            <div className="flex-shrink-0 mb-6 md:mb-0">
              <div className="bg-gray-800 rounded-xl p-8 w-56 h-56 flex flex-col items-center justify-center shadow-lg">
                <div className="text-sm text-gray-400">Final Score</div>
                <div className="text-5xl font-bold mt-3">{pct(data.final ?? data.final_score ?? data.score)}%</div>
                <div className="text-sm text-gray-300 mt-2">Overall performance</div>
              </div>
            </div>

            {/* Other scores and feedback */}
            <div className="flex-1">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-400">Emotion</div>
                  <div className="text-2xl font-bold mt-2">{pct(data.emotion ?? data.emotion_score)}%</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-400">Eye Contact</div>
                  <div className="text-2xl font-bold mt-2">{pct(data.eye ?? data.eye_score ?? data.eye_contact_score)}%</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-400">Posture</div>
                  <div className="text-2xl font-bold mt-2">{pct(data.posture ?? data.posture_score)}%</div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-lg font-medium mb-3">Feedback</h3>
                {(!data.feedback || data.feedback.length === 0) ? (
                  <div className="text-gray-400">No feedback available.</div>
                ) : (
                  <ul className="list-disc list-inside text-gray-200">
                    {data.feedback.map((f, i) => (
                      <li key={i} className="py-1">{f}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
          <div className="mt-6 flex justify-center">
            <DashboardButton />
          </div>
        </div>
      </div>
    </div>
  )
}


function DashboardButton() {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate('/dashboard')}
      className="px-5 py-3 rounded-lg bg-white/6 backdrop-blur-md border border-white/10 text-white font-medium shadow-md transition-all duration-200 hover:scale-105"
    >
      Go to Dashboard
    </button>
  )
}
