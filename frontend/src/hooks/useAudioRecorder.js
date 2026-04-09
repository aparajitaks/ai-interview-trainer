import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * useAudioRecorder
 * ----------------
 * Manages the full MediaRecorder lifecycle: request mic permission,
 * collect chunks, produce a Blob on stop.
 *
 * Usage:
 *   const { isRecording, audioBlob, startRecording, stopRecording, clearBlob } = useAudioRecorder()
 *
 * Notes:
 *   - Records as audio/webm (Chromium) or audio/mp4 (Safari).
 *   - Passes the chosen mimeType through so the backend knows the format.
 *   - The webcam stream is separate — this hook only captures audio.
 */
export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob,   setAudioBlob]   = useState(null)
  const [mimeType,    setMimeType]    = useState('audio/webm')
  const [permError,   setPermError]   = useState('')

  const recorderRef = useRef(null)
  const chunksRef   = useRef([])
  const streamRef   = useRef(null)

  // ── Start ────────────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setPermError('')
    setAudioBlob(null)
    chunksRef.current = []

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream
    } catch (err) {
      const msg =
        err.name === 'NotAllowedError'
          ? 'Microphone access denied. Please allow mic access and try again.'
          : `Could not access microphone: ${err.message}`
      setPermError(msg)
      return
    }

    // Pick the best supported MIME type
    const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
    const chosen    = preferred.find((m) => MediaRecorder.isTypeSupported(m)) ?? ''
    setMimeType(chosen || 'audio/webm')

    const recorder = new MediaRecorder(stream, chosen ? { mimeType: chosen } : undefined)

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
    }

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: chosen || 'audio/webm' })
      setAudioBlob(blob)
      // Release mic
      stream.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }

    recorder.start(200)   // emit chunks every 200 ms
    recorderRef.current = recorder
    setIsRecording(true)
  }, [])

  // ── Stop ─────────────────────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }
    setIsRecording(false)
  }, [])

  const forceStopRecording = useCallback(() => {
    try {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop()
      }
    } catch {
      // No-op: we still force-close tracks below.
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    recorderRef.current = null
    setIsRecording(false)
  }, [])

  // ── Clear ─────────────────────────────────────────────────────────────────
  const clearBlob = useCallback(() => setAudioBlob(null), [])

  useEffect(() => {
    return () => {
      forceStopRecording()
    }
  }, [forceStopRecording])

  return {
    isRecording,
    audioBlob,
    mimeType,
    permError,
    startRecording,
    stopRecording,
    forceStopRecording,
    clearBlob,
  }
}
