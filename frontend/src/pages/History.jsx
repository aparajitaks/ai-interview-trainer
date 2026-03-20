import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/api'

export default function History() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
      ; (async () => {
        try {
          console.log('history: loading')
          const resp = await client.get('/session/history')
          if (!mounted) return
          const data = resp.data || []
          if (!mounted) return
          // normalize a couple of possible shapes (old /results vs new /session/history)
          const itemsList = (data || []).map((it) => ({
            id: it.id || it.session_id || it.sessionId || it.session || null,
            session_id: it.session_id || it.id || it.sessionId || null,
            created_at: it.created_at || it.createdAt || it.timestamp || null,
            average_score: it.average_score ?? it.avg_score ?? it.score ?? null,
            role: it.role || 'candidate',
            raw: it,
          }))
          setItems(itemsList)
        } catch (err) {
          console.error('Failed to load history', err)
          setItems([])
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
                <div key={it.id || it.session_id} className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg transform transition-all duration-200 hover:scale-102">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-semibold">{`Interview ${it.session_id || it.id || ''}`}</div>
                      <div className="text-sm text-slate-300">{it.created_at ? new Date(it.created_at).toLocaleString() : ''}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">{Math.round((it.average_score ?? it.score ?? 0) * 100)}</div>
                      <div className="text-sm text-slate-300">Score</div>
                    </div>
                  </div>
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={() => {
                        const sid = it.session_id || it.id
                        if (sid) sessionStorage.setItem('aiit_session_id', sid)
                        navigate('/results')
                      }}
                      className="px-4 py-2 rounded-lg bg-white/6 text-white border border-white/10 hover:scale-105"
                    >
                      View
                    </button>
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
