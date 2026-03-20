import React, { useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/api'
import { AuthContext } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { login } = useContext(AuthContext)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const resp = await client.post('/auth/login', { email, password })
      const token = resp.data && resp.data.access_token
      if (token) {
        await login(token)
        navigate('/dashboard')
      } else {
        setError('Invalid response from server')
      }
    } catch (err) {
      console.error(err)
      setError(err?.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black p-8">
      <div className="w-full max-w-md">
        <div className="bg-gray-800 p-6 rounded-xl">
          <h2 className="text-2xl font-semibold text-white mb-4">Login</h2>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm text-gray-300">Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} className="w-full mt-1 p-2 rounded bg-gray-900 text-white border border-gray-700" />
            </div>
            <div>
              <label className="text-sm text-gray-300">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full mt-1 p-2 rounded bg-gray-900 text-white border border-gray-700" />
            </div>
            {error && <div className="text-red-400">{error}</div>}
            <div>
              <button type="submit" className="w-full py-2 rounded bg-indigo-600">Sign in</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
