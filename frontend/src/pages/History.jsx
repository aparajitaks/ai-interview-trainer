import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function History() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    fetch('http://127.0.0.1:8000/results')
      .then((r) => r.json())
      .then((data) => {
        if (!mounted) return
        setItems(data || [])
      })
      .catch((err) => {
        console.error('Failed to load history', err)
      })
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-white">Interview History</h1>
          <p className="mt-2 text-slate-300">Your recent interview sessions.</p>
        </div>

        {loading ? (
          <div className="text-center text-slate-300">Loading...</div>
        ) : (
          <div className="space-y-4">
            {items.length === 0 ? (
              <div className="text-center text-slate-400">No interviews yet.</div>
            ) : (
              items.map((it) => (
                <div key={it.id} className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg transform transition-all duration-200 hover:scale-102">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-semibold">{`Interview #${it.id}`}</div>
                      <div className="text-sm text-slate-300">{new Date(it.created_at).toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">{Math.round((it.score ?? 0) * 100) || it.score}</div>
                      <div className="text-sm text-slate-300">Score</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

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
