import React, { createContext, useState, useEffect } from 'react'
import client from '../api/api'

export const AuthContext = createContext({
  token: null,
  user: null,
  login: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('aiit_token'))
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (token) {
      // fetch user info
      client
        .get('/auth/me')
        .then((r) => setUser(r.data))
        .catch(() => setUser(null))
    } else {
      setUser(null)
    }
  }, [token])

  const login = async (access_token) => {
    if (!access_token) return
    localStorage.setItem('aiit_token', access_token)
    setToken(access_token)
    // client interceptor will pick token up automatically
    try {
      const resp = await client.get('/auth/me')
      setUser(resp.data)
    } catch (err) {
      setUser(null)
    }
  }

  const logout = () => {
    localStorage.removeItem('aiit_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>{children}</AuthContext.Provider>
  )
}
