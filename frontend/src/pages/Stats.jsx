import React from 'react'
import { useNavigate } from 'react-router-dom'

function StatCard({ title, value }) {
  return (
    <div className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-300">{title}</div>
          <div className="text-2xl font-bold text-white mt-1">{value}%</div>
        </div>
        <div className="w-40">
          <div className="h-3 bg-white/10 rounded-full overflow-hidden">
            <div className="h-3 bg-gradient-to-r from-indigo-500 to-pink-500 rounded-full" style={{ width: `${value}%` }} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Stats() {
  const navigate = useNavigate()

  const stats = [
    { id: 'emotion', title: 'Emotion Score', value: 82 },
    { id: 'posture', title: 'Posture Score', value: 74 },
    { id: 'eye', title: 'Eye Contact Score', value: 69 },
    { id: 'final', title: 'Final Score', value: 78 },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-white">Performance Stats</h1>
          <p className="mt-2 text-slate-300">Overview of your aggregated performance metrics.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {stats.map((s) => (
            <StatCard key={s.id} title={s.title} value={s.value} />
          ))}
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-5 py-3 rounded-lg bg-white/6 backdrop-blur-md border border-white/10 text-white font-medium shadow-md transition-all duration-200 hover:scale-105"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}
