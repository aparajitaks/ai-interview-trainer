import React from 'react'
import ScoreCard from '../components/ScoreCard'

export default function Result({ result }) {
  const data = result || {
    emotion: 0,
    eye: 0,
    posture: 0,
    final: 0,
    feedback: [],
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Interview Results</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <ScoreCard label="Emotion" value={data.emotion} />
        <ScoreCard label="Eye" value={data.eye} />
        <ScoreCard label="Posture" value={data.posture} />
        <ScoreCard label="Final" value={data.final} />
      </div>

      <div className="mt-4 bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-medium mb-2">Feedback</h3>
        <ul className="list-disc list-inside text-gray-200">
          {(data.feedback || []).map((f, i) => (
            <li key={i} className="py-1">{f}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
