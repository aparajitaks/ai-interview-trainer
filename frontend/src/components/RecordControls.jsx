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
    <div className="flex items-center justify-between bg-gray-800 rounded-lg p-4">
      <div>
        <button
          onClick={() => setRecording(true)}
          className="mr-3 px-4 py-2 rounded-full bg-red-600 hover:bg-red-500 text-white font-medium"
        >
          Record
        </button>
        <button
          onClick={() => setRecording(false)}
          className="px-4 py-2 rounded-full bg-gray-700 hover:bg-gray-600 text-white font-medium"
        >
          Stop
        </button>
      </div>

      <div className="text-gray-300">Timer: <span className="font-mono">{String(seconds).padStart(2, '0')}s</span></div>
    </div>
  )
}
