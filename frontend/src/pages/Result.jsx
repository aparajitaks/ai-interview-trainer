import React from 'react'
import ScoreCard from '../components/ScoreCard'

export default function Result() {
  const sample = {
    emotion: 0.72,
    eye: 0.58,
    posture: 0.86,
    final: 0.72,
    feedback: [
      'Maintain better eye contact',
      'Sit straight and keep good posture',
      'Try to show more confident facial expressions',
    ],
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Interview Results</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <ScoreCard label="Emotion" value={sample.emotion} />
        <ScoreCard label="Eye" value={sample.eye} />
        <ScoreCard label="Posture" value={sample.posture} />
        <ScoreCard label="Final" value={sample.final} />
      </div>

      <div className="mt-4 bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-medium mb-2">Feedback</h3>
        <ul className="list-disc list-inside text-gray-200">
          {sample.feedback.map((f, i) => (
            <li key={i} className="py-1">{f}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
