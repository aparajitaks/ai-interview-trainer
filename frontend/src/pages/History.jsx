import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function History() {
  const navigate = useNavigate()

  const items = [
    { id: 1, title: 'Interview 1', score: 78 },
    { id: 2, title: 'Interview 2', score: 65 },
    { id: 3, title: 'Interview 3', score: 90 },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-white">Interview History</h1>
          <p className="mt-2 text-slate-300">Your recent interview sessions.</p>
        </div>

        <div className="space-y-4">
          {items.map((it) => (
            <div key={it.id} className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg transform transition-all duration-200 hover:scale-102">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-semibold">{it.title}</div>
                  <div className="text-sm text-slate-300">Completed session</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-white">{it.score}</div>
                  <div className="text-sm text-slate-300">Score</div>
                </div>
              </div>
            </div>
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
