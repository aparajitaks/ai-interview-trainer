import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startSession } from '../api/api'
import { motion } from 'framer-motion'

const ROLES = ['ML', 'Frontend', 'Backend', 'HR', 'DSA']

export default function RoleSelect() {
  const [role, setRole] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const onStart = async () => {
    if (!role) return alert('Please select a role')
    try {
      setBusy(true)
      const data = await startSession(role.toLowerCase())
      // save session id in sessionStorage for interview page
      sessionStorage.setItem('aiit_session_id', data.session_id)
      sessionStorage.setItem('aiit_question', data.question || '')
      sessionStorage.setItem('aiit_question_id', data.question_id || '')
      navigate('/session')
    } catch (err) {
      console.error('start session failed', err)
      alert('Failed to start session')
    } finally {
      setBusy(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 flex items-center justify-center p-6 text-white">
      <div className="w-full max-w-4xl">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">AI Interview Trainer</h1>
            <p className="text-gray-300 mt-1">Practice with role-tailored interview questions</p>
          </div>
          <nav className="space-x-4">
            <a href="/" className="text-sm text-gray-300 hover:text-white">Home</a>
            <a href="/session" className="text-sm text-gray-300 hover:text-white">Interview</a>
            <a href="/results" className="text-sm text-gray-300 hover:text-white">Results</a>
          </nav>
        </header>

        <motion.section className="bg-gray-800 rounded-2xl shadow-lg p-8" initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
          <h2 className="text-3xl font-semibold mb-2">Select your role</h2>
          <p className="text-gray-400 mb-6">Pick a role to get questions tailored to that domain. Click a card to select.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            {ROLES.map((r) => (
              <motion.button
                key={r}
                onClick={() => setRole(r)}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                className={`relative p-6 rounded-2xl shadow-lg bg-gray-900 text-white transition transform hover:scale-105`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-lg font-semibold">{r}</div>
                    <div className="text-sm text-gray-400 mt-1">Practice {r} interview questions</div>
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${role === r ? 'bg-indigo-500 text-white' : 'bg-gray-700 text-gray-300'}`}>
                    {role === r ? '✓' : r[0]}
                  </div>
                </div>
              </motion.button>
            ))}
          </div>

          <div className="flex items-center justify-end">
            <button onClick={onStart} disabled={busy} className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-2xl shadow-lg text-white transition disabled:opacity-50">
              {busy ? 'Starting...' : 'Start Interview'}
            </button>
          </div>
        </motion.section>
      </div>
    </motion.div>
  )
}
