import React, { useEffect, useState } from 'react'
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
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        console.log('stats: loading')
        const resp = await fetch('http://127.0.0.1:8000/stats')
        if (!mounted) return
        if (!resp.ok) {
          const txt = await resp.text().catch(() => '')
          console.error('Failed to load stats - server error', resp.status, resp.statusText, txt)
          return
        }
        const data = await resp.json().catch(() => null)
        if (!mounted) return
        setStats(data)
      } catch (err) {
        console.error('Failed to load stats', err)
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-white">Performance Stats</h1>
          <p className="mt-2 text-slate-300">Overview of your aggregated performance metrics.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {loading ? (
            <div className="text-slate-300">Loading...</div>
          ) : stats ? (
            <>
              <StatCard title="Average Score" value={Math.round((stats.average_score ?? 0) * 100) || stats.average_score} />
              <StatCard title="Best Score" value={Math.round((stats.best_score ?? 0) * 100) || stats.best_score} />
              <StatCard title="Total Interviews" value={stats.total_interviews ?? 0} />
            </>
          ) : (
            <div className="text-slate-300">No stats available.</div>
          )}
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
