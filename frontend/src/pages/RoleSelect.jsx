import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startSession } from '../api/api'

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
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-2xl w-full bg-gray-800 p-8 rounded-lg shadow-lg">
        <h2 className="text-2xl font-semibold mb-4">Select Interview Role</h2>
        <p className="text-sm text-gray-400 mb-6">Choose the role you want to practice for. Questions will be tailored to this role.</p>
        <div className="grid grid-cols-2 gap-3 mb-6">
          {ROLES.map((r) => (
            <button
              key={r}
              onClick={() => setRole(r)}
              className={`py-3 px-4 rounded-lg text-left ${role === r ? 'bg-indigo-600' : 'bg-gray-700 hover:bg-gray-600'}`}>
              <div className="text-sm font-medium">{r}</div>
              <div className="text-xs text-gray-300 mt-1">Practice {r} interview questions</div>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-end">
          <button onClick={onStart} disabled={busy} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded">Start Interview</button>
        </div>
      </div>
    </div>
  )
}
