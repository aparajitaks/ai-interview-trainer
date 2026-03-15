import React from 'react'
import CameraBox from '../components/CameraBox'
import QuestionBox from '../components/QuestionBox'
import RecordControls from '../components/RecordControls'

export default function Interview() {
  return (
    <div className="min-h-screen bg-slate-900 text-gray-100 flex flex-col">
      {/* Top bar */}
      <header className="w-full bg-slate-950/40 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center">
          <h1 className="text-lg font-semibold">AI Interview Trainer</h1>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
          <div className="p-1">
            <CameraBox />
          </div>

          <div className="p-1">
            <QuestionBox />
          </div>
        </div>
      </main>

      {/* Bottom controls */}
      <footer className="w-full border-t border-slate-800 bg-slate-950/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <RecordControls />
        </div>
      </footer>
    </div>
  )
}
