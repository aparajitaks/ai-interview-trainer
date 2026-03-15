import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
  const navigate = useNavigate()

  const cards = [
    {
      key: 'start',
      title: 'Start Interview',
      desc: 'Begin a new practice interview',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-6.518 3.76A1 1 0 017 14.98V8.02a1 1 0 011.234-.97l6.518 1.72a1 1 0 010 1.398z" />
        </svg>
      ),
      onClick: () => navigate('/interview'),
    },
    {
      key: 'past',
      title: 'Past Interviews',
      desc: 'Browse your previous sessions',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7M16 3v4M8 3v4" />
        </svg>
      ),
      onClick: () => navigate('/results'),
    },
    {
      key: 'perf',
      title: 'Performance',
      desc: 'View aggregated performance metrics',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 12h2M12 20v-8m-4 4V8m8 8V4" />
        </svg>
      ),
      onClick: () => navigate('/stats'),
    },
    {
      key: 'settings',
      title: 'Settings',
      desc: 'Configure your preferences',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15.5A3.5 3.5 0 1112 8.5a3.5 3.5 0 010 7z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06A2 2 0 014.28 17.9l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82L4.21 6.7A2 2 0 016.27 3.87l.06.06a1.65 1.65 0 001.82.33h.09A1.65 1.65 0 0010.75 4V3a2 2 0 014 0v.09c.11.56.33 1.08.7 1.51.35.41.83.72 1.36.9h.09a1.65 1.65 0 001.82-.33l.06-.06A2 2 0 0119.72 6.1l-.06.06c-.21.16-.38.36-.52.58" />
        </svg>
      ),
      onClick: () => navigate('/settings'),
    },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-900 via-slate-800 to-gray-900 p-8">
      <div className="max-w-6xl w-full">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-extrabold text-white">AI Interview Trainer Dashboard</h1>
          <p className="mt-2 text-slate-300">A quick overview of your interview activities and performance.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map((c) => (
            <div
              key={c.key}
              onClick={c.onClick}
              role="button"
              tabIndex={0}
              className="cursor-pointer transform transition-all duration-300 hover:scale-105 hover:shadow-2xl rounded-xl p-6 bg-white/5 backdrop-blur-md border border-white/6"
            >
              <div className="flex items-start">
                <div className="p-3 rounded-lg bg-gradient-to-br from-indigo-600 to-pink-500 text-white mr-4">{c.icon}</div>
                <div className="flex-1 text-left">
                  <h3 className="text-lg font-semibold text-white">{c.title}</h3>
                  <p className="text-sm text-slate-300 mt-1">{c.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
