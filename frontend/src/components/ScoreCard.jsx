import React from 'react'

export default function ScoreCard({ label, value }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div className="bg-gray-800 rounded-lg p-4 text-center">
      <div className="text-sm text-gray-400">{label}</div>
      <div className="text-3xl font-bold mt-2">{pct}%</div>
      <div className="w-full bg-gray-700 h-2 rounded-full mt-4 overflow-hidden">
        <div className="bg-indigo-500 h-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
