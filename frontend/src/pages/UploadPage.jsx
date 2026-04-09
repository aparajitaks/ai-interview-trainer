import { useState, useCallback, useRef } from 'react'
import { useNavigate }                   from 'react-router-dom'
import { motion, AnimatePresence }       from 'framer-motion'
import PageWrapper                       from '../layouts/PageWrapper.jsx'
import Spinner                           from '../components/ui/Spinner.jsx'
import { useAnalysis }                   from '../hooks/useAnalysis.js'

/* ── Helpers ────────────────────────────────────────────────────────────── */
const ACCEPTED = ['video/mp4','video/quicktime','video/avi','video/x-msvideo','video/x-matroska','video/webm']
const ACCEPTED_EXT = /\.(mp4|mov|avi|mkv|webm)$/i

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isValidVideo(file) {
  return ACCEPTED.includes(file.type) || ACCEPTED_EXT.test(file.name)
}

/* ═══════════════════════════════════════════════════════════════════════════
   UploadPage
   ════════════════════════════════════════════════════════════════════════ */
export default function UploadPage() {
  const navigate                              = useNavigate()
  const { analyze, isLoading, progress, error } = useAnalysis()
  const [file,       setFile]                 = useState(null)
  const [isDragging, setIsDragging]           = useState(false)
  const [fileError,  setFileError]            = useState('')
  const inputRef                              = useRef(null)

  /* ── File selection ───────────────────────────────────────────────────── */
  const handleFile = useCallback((f) => {
    if (!f) return
    if (!isValidVideo(f)) {
      setFileError('Unsupported format. Please upload an MP4, MOV, AVI, MKV, or WebM file.')
      return
    }
    if (f.size > 100 * 1024 * 1024) {
      setFileError('File too large. Max upload size is 100 MB.')
      return
    }
    setFileError('')
    setFile(f)
  }, [])

  /* ── Drag & drop ───────────────────────────────────────────────────────── */
  const onDragOver  = (e) => { e.preventDefault(); setIsDragging(true)  }
  const onDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const onDrop      = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  /* ── Analyse ───────────────────────────────────────────────────────────── */
  const handleAnalyze = async () => {
    if (!file || isLoading) return
    try {
      const result = await analyze(file)
      navigate('/results', { state: { result } })
    } catch {
      /* error already stored in the hook */
    }
  }

  /* ── Derived UI state ──────────────────────────────────────────────────── */
  const dropLabel     = isDragging ? 'Release to upload' : 'Drop your video here'
  const buttonLabel   = isLoading  ? `Analyzing… ${progress < 100 ? `(${progress}%)` : ''}` : 'Analyze Interview →'
  const buttonDisabled= !file || isLoading

  return (
    <PageWrapper>
      <div className="min-h-screen bg-[#0A0F1E] flex flex-col items-center justify-center px-4 py-20">

        {/* Ambient orbs */}
        <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
          <div className="absolute top-1/3 -left-40 w-[500px] h-[500px]
                          bg-indigo-700/10 rounded-full blur-[100px]" />
          <div className="absolute bottom-1/3 -right-40 w-[400px] h-[400px]
                          bg-purple-700/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 w-full max-w-xl">

          {/* ── Header ────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0   }}
            transition={{ duration: 0.4 }}
            className="text-center mb-10"
          >
            {/* Back link */}
            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center gap-1 text-sm text-gray-500
                         hover:text-gray-300 transition-colors mb-6"
            >
              ← Home
            </button>

            <h1 className="text-4xl font-black tracking-tight">
              Upload Your{' '}
              <span className="gradient-text">Interview Video</span>
            </h1>
            <p className="text-gray-400 mt-3 text-base">
              We'll analyse emotion, eye contact, and posture automatically.
            </p>
          </motion.div>

          {/* ── Drop zone ─────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0  }}
            transition={{ delay: 0.15, duration: 0.4 }}

            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => !file && !isLoading && inputRef.current?.click()}

            className={`
              relative rounded-3xl border-2 border-dashed p-14
              text-center cursor-pointer select-none
              transition-all duration-300 ease-out
              ${isDragging
                ? 'border-indigo-400/80 bg-indigo-500/[0.08] scale-[1.015]'
                : file
                  ? 'border-green-500/40  bg-green-500/[0.04] cursor-default'
                  : 'border-white/10 bg-white/[0.02] hover:border-indigo-500/40 hover:bg-indigo-500/[0.04]'
              }
            `}
          >
            {/* Dragging inner glow */}
            {isDragging && (
              <div className="absolute inset-0 rounded-3xl pointer-events-none
                              bg-indigo-500/5 blur-2xl" />
            )}

            <AnimatePresence mode="wait">

              {/* Loading state */}
              {isLoading && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{    opacity: 0 }}
                  className="flex flex-col items-center gap-5"
                >
                  <Spinner size="xl" />
                  <div>
                    <p className="text-indigo-300 font-semibold text-xl">
                      Analysing your interview…
                    </p>
                    <p className="text-gray-500 text-sm mt-1">
                      {progress < 100
                        ? `Uploading — ${progress}%`
                        : 'Running AI pipeline — this may take a moment'}
                    </p>
                  </div>

                  {/* Upload progress bar */}
                  {progress < 100 && (
                    <div className="w-48 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  )}
                </motion.div>
              )}

              {/* File selected */}
              {!isLoading && file && (
                <motion.div
                  key="file"
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1    }}
                  exit={{    opacity: 0, scale: 0.95  }}
                  className="flex flex-col items-center gap-3"
                >
                  <div className="w-16 h-16 rounded-2xl bg-green-500/[0.12]
                                  border border-green-500/20
                                  flex items-center justify-center text-3xl">
                    🎬
                  </div>
                  <div>
                    <p className="font-semibold text-white text-lg leading-tight">
                      {file.name}
                    </p>
                    <p className="text-gray-400 text-sm mt-1">{formatBytes(file.size)}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null) }}
                    className="text-xs text-red-400/70 hover:text-red-400
                               underline underline-offset-2 transition-colors"
                  >
                    Remove file
                  </button>
                </motion.div>
              )}

              {/* Empty state */}
              {!isLoading && !file && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{    opacity: 0 }}
                  className="flex flex-col items-center gap-4"
                >
                  <div className="w-20 h-20 glass rounded-3xl
                                  flex items-center justify-center text-5xl mb-1
                                  transition-transform duration-300
                                  group-hover:scale-110">
                    {isDragging ? '⬇️' : '📹'}
                  </div>
                  <div>
                    <p className="text-white font-semibold text-xl">{dropLabel}</p>
                    <p className="text-gray-500 mt-2 text-sm">
                      or{' '}
                      <span className="text-indigo-400 font-medium
                                       underline underline-offset-2 cursor-pointer">
                        browse files
                      </span>
                    </p>
                  </div>
                  <p className="text-xs text-gray-700 mt-1">
                    MP4 · MOV · AVI · MKV · WebM &nbsp;·&nbsp; Max 100 MB
                  </p>
                </motion.div>
              )}

            </AnimatePresence>
          </motion.div>

          {/* Hidden file input */}
          <input
            ref={inputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/avi,.mp4,.mov,.avi,.mkv,.webm"
            className="sr-only"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />

          {/* ── Errors ────────────────────────────────────────────────── */}
          <AnimatePresence>
            {(fileError || error) && (
              <motion.div
                initial={{ opacity: 0, y: 8  }}
                animate={{ opacity: 1, y: 0  }}
                exit={{    opacity: 0, y: -4 }}
                className="mt-4 glass rounded-xl px-5 py-3
                           border border-red-500/20 bg-red-500/[0.06]"
              >
                <p className="text-red-400 text-sm text-center">
                  ⚠️ {fileError || error}
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Analyse button ─────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-5"
          >
            <button
              onClick={handleAnalyze}
              disabled={buttonDisabled}
              className={`
                w-full py-4 rounded-2xl font-bold text-lg
                transition-all duration-200 flex items-center justify-center gap-3
                ${buttonDisabled
                  ? 'glass text-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white ' +
                    'hover:from-indigo-500 hover:to-purple-500 ' +
                    'shadow-xl shadow-indigo-500/20 active:scale-[0.98]'
                }
              `}
            >
              {isLoading && <Spinner size="sm" />}
              {buttonLabel}
            </button>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  )
}
