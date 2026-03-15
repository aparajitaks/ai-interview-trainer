import React, { useState, useEffect } from 'react'

export default function RecordControls() {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    let t = null
    if (recording) {
      t = setInterval(() => setSeconds((s) => s + 1), 1000)
    } else {
      setSeconds(0)
    }
    return () => clearInterval(t)
  }, [recording])

  return (
    <div className="flex items-center justify-center space-x-6">
      <div className="flex items-center space-x-3">
        <button
          onClick={() => setRecording(true)}
          aria-pressed={recording}
          className="flex items-center justify-center w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white shadow-md"
          title="Start recording"
        >
          {/* red circle */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8" />
          </svg>
        </button>

        <button
          onClick={() => setRecording(false)}
          className="flex items-center justify-center w-14 h-14 rounded-full bg-gray-700 hover:bg-gray-600 text-white shadow-sm"
          title="Stop recording"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2" strokeWidth="2" />
          </svg>
        </button>
      </div>

      <div className="ml-4 text-gray-300 flex items-center">
        <div className="text-sm text-gray-400">Timer</div>
        <div className="ml-3 font-mono text-lg">{String(seconds).padStart(2, '0')}s</div>
      </div>
    </div>
  )
}
