import { useEffect, useRef, useState } from 'react'

/**
 * WebcamPreview
 * -------------
 * Lightweight webcam preview with no CV processing.
 * - Starts camera on mount
 * - Stops camera on unmount
 */
export default function WebcamPreview({ className = '' }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [cameraError, setCameraError] = useState(false)

  useEffect(() => {
    let cancelled = false

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) videoRef.current.srcObject = stream
      } catch {
        setCameraError(true)
      }
    }

    startCamera()

    return () => {
      cancelled = true
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [])

  return (
    <div className={`glass rounded-xl overflow-hidden ${className}`}>
      {cameraError ? (
        <div className="h-full w-full min-h-[140px] flex items-center justify-center px-3 py-4 text-center text-xs text-gray-400">
          Camera unavailable
        </div>
      ) : (
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-full object-cover"
        />
      )}
    </div>
  )
}
