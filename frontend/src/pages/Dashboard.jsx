import React, { useEffect, useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/api'
import { AuthContext } from '../context/AuthContext'

export default function Dashboard() {
  const navigate = useNavigate()
  const { user, logout } = useContext(AuthContext)
  const [stats, setStats] = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    let mounted = true
    client
      .get('/stats')
      .then((r) => mounted && setStats(r.data))
      .catch((err) => console.error('Failed to load stats', err))

    client
      .get('/session/history')
      .then((r) => mounted && setHistory(r.data || []))
      .catch((err) => console.error('Failed to load session history', err))

    return () => {
      mounted = false
    }
  }, [])

  const cards = [
    { key: 'start', title: 'Start Interview', desc: 'Begin a new practice interview', icon: '🎤', onClick: () => navigate('/interview') },
    { key: 'results', title: 'View Results', desc: 'See latest interview results', icon: '📊', onClick: () => navigate('/result') },
    { key: 'history', title: 'History', desc: 'Your interview history', icon: '📚', onClick: () => navigate('/history') },
    { key: 'performance', title: 'Performance Stats', desc: 'Aggregated performance metrics', icon: '📈', onClick: () => navigate('/stats') },
    { key: 'past', title: 'Past Interviews', desc: 'Browse previous sessions', icon: '🗂️', onClick: () => navigate('/history') },
    { key: 'settings', title: 'Settings', desc: 'Configure preferences', icon: '⚙️', onClick: () => navigate('/settings') },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="max-w-6xl w-full">
        <div className="text-center mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-extrabold text-white">AI Interview Trainer Dashboard</h1>
            <p className="mt-2 text-slate-300">A quick overview of your interview activities and performance.</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-slate-300">{user ? user.email : ''}</div>
            <button onClick={() => logout()} className="mt-2 px-3 py-1 rounded bg-white/6">Sign out</button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-6">
          {cards.map((c) => (
            <div key={c.key} className="relative">
              {/* gradient border */}
              <div className="rounded-xl p-1 bg-gradient-to-br from-indigo-600 via-pink-500 to-amber-400 shadow-lg">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={c.onClick}
                  onKeyDown={(e) => e.key === 'Enter' && c.onClick()}
                  className="group block transform transition-all duration-300 hover:scale-105 rounded-lg p-6 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg"
                >
                  <div className="flex items-start">
                    <div className="flex-shrink-0 mr-4">
                      <div className="w-12 h-12 rounded-md flex items-center justify-center text-2xl bg-white/8 group-hover:scale-110 transform transition-all duration-300">
                        <span className="select-none">{c.icon}</span>
                      </div>
                    </div>
                    <div className="flex-1 text-left">
                      <h3 className="text-lg font-semibold text-white">{c.title}</h3>
                      <p className="text-sm text-slate-300 mt-1">{c.desc}</p>
                    </div>
                  </div>
                </div>
              </div>
              {/* subtle glow */}
              <div className="absolute inset-0 rounded-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
          ))}
        </div>
        
        {/* Summary cards */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg text-center">
            <div className="text-sm text-slate-300">Total Interviews</div>
            <div className="text-2xl font-bold text-white">{stats ? stats.total_interviews : '—'}</div>
          </div>
          <div className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg text-center">
            <div className="text-sm text-slate-300">Average Score</div>
            <div className="text-2xl font-bold text-white">{stats ? Math.round((stats.average_score ?? 0) * 100) : '—'}</div>
          </div>
          <div className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg text-center">
            <div className="text-sm text-slate-300">Best Score</div>
            <div className="text-2xl font-bold text-white">{stats ? Math.round((stats.best_score ?? 0) * 100) : '—'}</div>
          </div>
        </div>

        <div className="mt-8">
          <h3 className="text-xl text-white mb-3">Your recent sessions</h3>
          <div className="space-y-3">
            {history.length === 0 && <div className="text-slate-400">No sessions yet.</div>}
            {history.map((s) => (
              <div key={s.session_id} className="p-3 rounded bg-white/6 flex justify-between">
                <div>
                  <div className="text-white">{s.role || '—'}</div>
                  <div className="text-sm text-slate-300">{new Date(s.created_at).toLocaleString()}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-semibold">{Math.round((s.average_score ?? 0) * 100)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
