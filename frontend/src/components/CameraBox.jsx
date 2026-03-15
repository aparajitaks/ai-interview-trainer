import React, { useEffect, useRef, useState } from 'react'

export default function CameraBox({ onStreamAvailable }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true

    async function startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError('Camera not supported')
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
        if (!mounted) return
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          // try play (some browsers require a user gesture; this is best-effort)
          const p = videoRef.current.play()
          if (p && p.catch) p.catch(() => {})
        }
        // notify parent if provided so others (RecordControls) can use the same stream
        if (typeof onStreamAvailable === 'function') {
          try {
            onStreamAvailable(stream)
          } catch (_) {
            // ignore
          }
        }
      } catch (err) {
        console.error('getUserMedia error', err)
        setError('Unable to access camera')
      }
    }

    startCamera()

    return () => {
      mounted = false
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      if (videoRef.current) {
        try {
          videoRef.current.srcObject = null
        } catch (e) {
          // ignore
        }
      }
    }
  }, [])

  return (
    <div className="w-full h-full bg-gray-800 rounded-xl shadow-lg flex items-center justify-center">
      <div className="w-full max-w-3xl p-6">
        <div className="bg-gray-900 rounded-lg aspect-video flex items-center justify-center border border-gray-700 overflow-hidden">
          {error ? (
            <span className="text-gray-400 text-lg font-medium">{error}</span>
          ) : (
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              playsInline
              muted
              autoPlay
            />
          )}
        </div>
      </div>
    </div>
  )
}
