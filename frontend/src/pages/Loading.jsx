import React from 'react'

export default function Loading() {
  return (
    <div className="min-h-screen bg-slate-900 text-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="flex items-center justify-center mb-6">
          <div className="w-20 h-20 rounded-full border-4 border-slate-700 border-t-transparent animate-spin"></div>
        </div>
        <h2 className="text-2xl font-semibold mb-2">Analyzing your interview...</h2>
        <p className="text-sm text-slate-400">This may take a few moments. We&apos;ll show your results when analysis completes.</p>
      </div>
    </div>
  )
}
