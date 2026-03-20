import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function Home() {
  const nav = useNavigate()
  return (
    <div className="flex items-center justify-center h-[70vh]">
      <div className="w-full max-w-xl text-center">
        <h1 className="text-4xl font-bold mb-6">AI Interview Trainer</h1>
        <p className="text-gray-400 mb-8">Practice video interviews and get instant feedback on emotion, eye contact and posture.</p>
        <button
          onClick={() => nav('/role')}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-full text-white font-medium shadow-lg"
        >
          Start Interview
        </button>
        <div className="mt-4">
          <button
            onClick={() => nav('/dashboard')}
            className="px-5 py-2 rounded-md transition-all duration-200 bg-white/6 backdrop-blur-md border border-white/10 text-white hover:scale-105 hover:shadow-lg"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}
