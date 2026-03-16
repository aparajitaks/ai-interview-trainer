import React from 'react'

export default function Loading({ status = 'analyzing' }) {
  const message = (() => {
    switch (status) {
      case 'uploading':
        return { title: 'Uploading your recording...', subtitle: 'Sending your video to the analysis server.' }
      case 'analyzing':
        return { title: 'Analyzing your interview...', subtitle: "This may take a few moments. We'll show your results when analysis completes." }
      case 'error':
        return { title: 'Something went wrong', subtitle: 'An error occurred while processing your interview. Please try again.' }
      case 'recording':
        return { title: 'Recording...', subtitle: 'Recording in progress. Stop when you are done.' }
      case 'done':
        return { title: 'Analysis complete', subtitle: 'Redirecting to results...' }
      default:
        return { title: 'Working...', subtitle: "Please wait while we process your interview." }
    }
  })()

  return (
    <div className="min-h-screen bg-slate-900 text-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="flex items-center justify-center mb-6">
          <div className="w-20 h-20 rounded-full border-4 border-slate-700 border-t-transparent animate-spin"></div>
        </div>
        <h2 className="text-2xl font-semibold mb-2">{message.title}</h2>
        <p className="text-sm text-slate-400">{message.subtitle}</p>
      </div>
    </div>
  )
}
