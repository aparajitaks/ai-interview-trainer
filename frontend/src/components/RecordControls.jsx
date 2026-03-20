import React, { useState, useEffect, useRef } from 'react'
import { uploadAnalyze } from '../api/api'

export default function RecordControls({ stream, onAnalysisComplete, setLoading, setStatus }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [recordedBlob, setRecordedBlob] = useState(null)
  // local busy flag to prevent multiple simultaneous uploads/records
  const [busy, setBusy] = useState(false)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    let t = null
    if (recording) {
      t = setInterval(() => setSeconds((s) => s + 1), 1000)
    } else {
      setSeconds(0)
    }
    return () => clearInterval(t)
  }, [recording])

  const startRecording = () => {
    if (busy) return
    if (!stream) {
      console.warn('No camera stream available to record')
      if (typeof setStatus === 'function') setStatus('error')
      return
    }

    // stop existing recorder if any
    if (mediaRecorderRef.current) {
      try {
        mediaRecorderRef.current.stop()
      } catch (_) {}
      mediaRecorderRef.current = null
      chunksRef.current = []
    }

    let options = {}
    if (typeof MediaRecorder !== 'undefined') {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
        options.mimeType = 'video/webm;codecs=vp9'
      } else if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
        options.mimeType = 'video/webm;codecs=vp8'
      } else {
        options.mimeType = 'video/webm'
      }
    }

    try {
      setBusy(true)
      if (typeof setStatus === 'function') setStatus('recording')
      const mr = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mr
      chunksRef.current = []

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: options.mimeType || 'video/webm' })
        setRecordedBlob(blob)
        chunksRef.current = []
        mediaRecorderRef.current = null
        console.log('video recorded')

        // Upload recorded video to backend analyze endpoint
        ;(async () => {
          // signal loading state in parent
          if (typeof setLoading === 'function') {
            try {
              setLoading(true)
            } catch (e) {}
          }

          if (typeof setStatus === 'function') setStatus('uploading')

          try {
            console.log('upload start')
            console.log('sending video for analysis')

            let data = null
            try {
              data = await uploadAnalyze(blob)
            } catch (err) {
              console.log('upload failed', err)
              if (typeof setStatus === 'function') setStatus('error')
              if (typeof onAnalysisComplete === 'function') {
                try {
                  onAnalysisComplete({ error: String(err) })
                } catch (_) {}
              }
              return
            }

            console.log('upload done')
            console.log('analysis result', data)
            // mark analyzing/done states briefly
            if (typeof setStatus === 'function') setStatus('analyzing')

            // notify parent component (Interview) if provided
            if (typeof onAnalysisComplete === 'function') {
              try {
                onAnalysisComplete(data)
              } catch (e) {
                // ignore
              }
            }

            if (typeof setStatus === 'function') setStatus('done')
          } catch (err) {
            console.log('upload failed', err)
            if (typeof setStatus === 'function') setStatus('error')
            if (typeof onAnalysisComplete === 'function') {
              try {
                onAnalysisComplete({ error: String(err) })
              } catch (_) {}
            }
          } finally {
            // ensure loading is cleared if onAnalysisComplete did not already handle it
            // (Interview's handler will attempt to clear loading as well)
            if (typeof setLoading === 'function') {
              try {
                setLoading(false)
              } catch (e) {}
            }
            setBusy(false)
          }
        })()
      }

      mr.start()
      setRecording(true)
    } catch (err) {
      console.error('MediaRecorder start failed', err)
      // if starting the recorder failed, clear busy so UI isn't stuck
      try {
        setBusy(false)
      } catch (_) {}
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop()
      } catch (e) {
        console.warn('error stopping recorder', e)
      }
    }
    setRecording(false)
    if (typeof setStatus === 'function') setStatus('idle')
  }

  return (
    <div className="flex items-center justify-center space-x-6">
      <div className="flex items-center space-x-3">
        <button
          onClick={startRecording}
          aria-pressed={recording}
          disabled={recording || busy}
          className={`flex items-center justify-center w-14 h-14 rounded-full text-white shadow-md ${recording || busy ? 'bg-red-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-500'}`}
          title="Start recording"
        >
          {/* red circle */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8" />
          </svg>
        </button>

        <button
          onClick={stopRecording}
          disabled={!recording}
          className={`flex items-center justify-center w-14 h-14 rounded-full text-white shadow-sm ${!recording ? 'bg-gray-600 cursor-not-allowed' : 'bg-gray-700 hover:bg-gray-600'}`}
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
