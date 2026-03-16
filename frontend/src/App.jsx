import React, { useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Interview from './pages/Interview'
import Result from './pages/Result'
import Loading from './pages/Loading'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Stats from './pages/Stats'
import Settings from './pages/Settings'

export default function App() {
  const [analysisResult, setAnalysisResult] = useState(null)
  const [loading, setLoading] = useState(false)
  // more granular UI status for the loading screen: 'idle'|'recording'|'uploading'|'analyzing'|'error'|'done'
  const [status, setStatus] = useState('idle')

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans">
      <nav className="p-4 border-b border-gray-800">
        <div className="container mx-auto flex items-center justify-between">
          <Link to="/" className="text-lg font-semibold">AI Interview Trainer</Link>
          <div className="space-x-3">
            <Link to="/" className="text-sm text-gray-300 hover:text-white">Home</Link>
            <Link to="/interview" className="text-sm text-gray-300 hover:text-white">Interview</Link>
            <Link to="/result" className="text-sm text-gray-300 hover:text-white">Result</Link>
          </div>
        </div>
      </nav>

      <main className="container mx-auto p-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/interview"
            element={<Interview setAnalysisResult={setAnalysisResult} loading={loading} setLoading={setLoading} setStatus={setStatus} />}
          />
          <Route path="/loading" element={<Loading status={status} />} />
          <Route path="/result" element={<Result result={analysisResult} />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
