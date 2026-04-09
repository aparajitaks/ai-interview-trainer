import { useEffect, useCallback, useRef, useState } from 'react'
import { useNavigate }                    from 'react-router-dom'
import { motion, AnimatePresence }        from 'framer-motion'
import PageWrapper                        from '../layouts/PageWrapper.jsx'
import Spinner                            from '../components/ui/Spinner.jsx'
import AnimatedBar                        from '../components/ui/AnimatedBar.jsx'
import Badge                              from '../components/ui/Badge.jsx'
import ProgressHeader                     from '../components/ui/ProgressHeader.jsx'
import WebcamPreview                      from '../components/ui/WebcamPreview.jsx'
import CodeEditor                         from '../components/CodeEditor.jsx'
import { useInterview, STATES }           from '../hooks/useInterview.js'
import { useAudioRecorder }              from '../hooks/useAudioRecorder.js'

/* ── Role presets ────────────────────────────────────────────────────────── */
const ROLES = [
  'Software Engineer',
  'AI / ML Engineer',
  'Data Engineer',
  'Frontend Engineer',
  'Backend Engineer',
  'Product Manager',
  'Data Scientist',
  'DevOps / Platform Engineer',
]

/* ── Timer formatter ─────────────────────────────────────────────────────── */
const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

/* ── Score colour ────────────────────────────────────────────────────────── */
const scoreColour = (s) =>
  s >= 8 ? 'text-green-400' : s >= 6 ? 'text-yellow-400' : 'text-red-400'

/* ── Fade-up animation helper ────────────────────────────────────────────── */
const fu = (d = 0) => ({
  initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 },
  transition: { delay: d, duration: 0.4 },
})

/* ══════════════════════════════════════════════════════════════════════════
   LiveInterviewPage
   ══════════════════════════════════════════════════════════════════════ */
export default function LiveInterviewPage() {
  const navigate = useNavigate()

  /* Interview state machine */
  const {
    phase, sessionId, role, setRole,
    question, questionType, roundNumber, totalRounds,
    lastTranscript, lastFeedback, lastScore,
    finalResult, error, isFinalizingLastAnswer, elapsed,
    isFollowUp, followUpReason,
    begin, onRecordingStarted, submitAudio, submitCode, skip, quit, reset,
  } = useInterview()

  /* Whether the interview is in an active answering phase */
  const isInterviewActive = phase === STATES.QUESTION || phase === STATES.RECORDING || phase === STATES.PROCESSING



  /* ── 15-second inactivity auto-skip timer ────────────────────────── */
  const AUTO_SKIP_SECS        = 15
  const [countdown, setCountdown] = useState(AUTO_SKIP_SECS)
  const [autoSkipAlert, setAutoSkipAlert] = useState(false)
  const countdownRef = useRef(null)

  // Start / reset countdown whenever a new question appears.
  // Clear it if the user starts recording or phase changes away from QUESTION.
  useEffect(() => {
    if (phase !== STATES.QUESTION || questionType === 'coding') {
      clearInterval(countdownRef.current)
      setCountdown(AUTO_SKIP_SECS)
      setAutoSkipAlert(false)
      return
    }

    // Fresh question — start counting down from AUTO_SKIP_SECS
    setCountdown(AUTO_SKIP_SECS)
    setAutoSkipAlert(false)
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownRef.current)
          setAutoSkipAlert(true)
          skip()          // fire skip when countdown hits 0
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(countdownRef.current)
  }, [phase, question, questionType]) // restarts every time a new question loads

  // Reset countdown when user clicks record (shows they are active)
  const handleStartRecording = async () => {
    clearInterval(countdownRef.current)
    setCountdown(AUTO_SKIP_SECS)
    setAutoSkipAlert(false)
    await startRecording()
    onRecordingStarted()
  }

  /* Audio recorder */
  const {
    audioBlob,
    permError, startRecording, stopRecording, clearBlob,
  } = useAudioRecorder()

  /* ── Auto-end when 30-minute timer expires ─────────────────────────── */
  const handleTimeUp = useCallback(() => {
    quit()
  }, [quit])

  /* When a new audio blob is ready, submit it automatically */
  useEffect(() => {
    if (audioBlob && phase === STATES.RECORDING) {
      submitAudio(audioBlob).then(clearBlob)
    }
  }, [audioBlob, phase, submitAudio, clearBlob])

  const handleStopRecording = () => stopRecording()
  const handleEndInterview = () => {
    quit()
  }

  /* ═════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════ */
  return (
    <PageWrapper>
      <div className="min-h-screen bg-[#0A0F1E] px-4 py-16 overflow-x-hidden">

        {/* Ambient orbs */}
        <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-purple-800/10 rounded-full blur-[120px]" />
          <div className="absolute top-2/3 -right-40 w-[500px] h-[500px] bg-indigo-800/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-3xl mx-auto">

          {/* ── IDLE ─────────────────────────────────────────────────── */}
          <AnimatePresence mode="wait">
          {phase === STATES.IDLE && (
            <motion.div key="idle" {...fu(0)} className="max-w-lg mx-auto text-center">
              <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-8 inline-flex items-center gap-1">
                ← Home
              </button>

              <Badge variant="live" >AI Live Interview</Badge>

              <h1 className="text-5xl font-black tracking-tight mt-6 mb-3">
                Start Your <span className="gradient-text">Live Interview</span>
              </h1>
              <p className="text-gray-400 mb-10">
                The AI will ask {totalRounds} progressive questions. Answer via your microphone.
                No account needed.
              </p>

              {/* Role selector */}
              <div className="glass rounded-2xl p-6 mb-6 text-left">
                <label className="metric-label block mb-3">Select your role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl
                             px-4 py-3 text-white text-base outline-none
                             focus:border-indigo-500/50 transition-colors cursor-pointer"
                >
                  {ROLES.map((r) => <option key={r} value={r} className="bg-[#1a1a2e]">{r}</option>)}
                </select>
                <p className="text-gray-600 text-xs mt-2">
                  Questions will be tailored to this role.
                </p>
              </div>

              <motion.button
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                onClick={() => begin(role, 5)}
                className="w-full py-4 rounded-2xl font-bold text-lg text-white
                           bg-gradient-to-r from-purple-600 to-indigo-600
                           hover:from-purple-500 hover:to-indigo-500
                           shadow-xl shadow-purple-500/20 transition-all"
              >
                Start Live Interview →
              </motion.button>
            </motion.div>
          )}

          {/* ── STARTING ─────────────────────────────────────────────── */}
          {phase === STATES.STARTING && (
            <motion.div key="starting" {...fu(0)} className="flex flex-col items-center gap-6 py-20">
              <Spinner size="xl" />
              <p className="text-indigo-300 font-semibold text-xl">Connecting to AI Interviewer…</p>
              <p className="text-gray-600 text-sm">Preparing your first question</p>
            </motion.div>
          )}

          {/* ── QUESTION / RECORDING / PROCESSING ────────────────────── */}
          {isInterviewActive && (
            <motion.div key="active" {...fu(0)}>
              <div className="flex flex-col lg:flex-row gap-6 items-start">
                {/* Left section: main interview content */}
                <div className="flex-1 w-full">
                  {/* Progress header with timer + progress bar */}
                  <ProgressHeader
                    roundNumber={roundNumber}
                    totalRounds={totalRounds}
                    isTimerRunning={isInterviewActive}
                    onTimeUp={handleTimeUp}
                  />

                  {/* Status badge row */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      {phase === STATES.RECORDING
                        ? <Badge variant="live">Recording</Badge>
                        : phase === STATES.PROCESSING
                          ? <Badge variant="warning">⚙️ Processing</Badge>
                          : <Badge variant="success">Ready to Answer</Badge>
                      }
                    </div>
                    <button onClick={handleEndInterview} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
                      End Interview
                    </button>
                  </div>

                  {phase === STATES.QUESTION && questionType !== 'coding' && (
                    <p className="text-sm text-gray-400 mb-5">
                      Answer using your voice. Recording starts when you click <span className="text-white font-medium">Start Answering</span>.
                    </p>
                  )}

                  <div className="mb-6">
                    <div className="glass rounded-2xl p-8 md:p-10 flex flex-col justify-between min-h-[280px]">

                  {/* Follow-up indicator + label */}
                  <div className="flex items-center gap-2 mb-4">
                    <p className="metric-label">AI Question</p>
                    {isFollowUp && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                                   bg-amber-500/15 border border-amber-500/30
                                   text-amber-400 text-[10px] font-bold uppercase tracking-wider"
                      >
                        <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <path d="M9 5l7 7-7 7" />
                        </svg>
                        Follow-up
                      </motion.span>
                    )}
                  </div>

                  <AnimatePresence mode="wait">
                    <motion.p
                      key={question}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{    opacity: 0, y: -6 }}
                      className="text-white text-2xl md:text-3xl font-semibold leading-relaxed flex-1"
                    >
                      {question || '…'}
                    </motion.p>
                  </AnimatePresence>

                  {phase === STATES.PROCESSING && (
                    <div className="mt-5 flex items-center gap-2 text-indigo-300">
                      <Spinner size="sm" />
                      <span className="text-sm">
                        {isFinalizingLastAnswer ? 'Processing your final answer...' : 'AI is analyzing your answer...'}
                      </span>
                    </div>
                  )}

                  {/* Timer */}
                  {phase === STATES.RECORDING && (
                    <div className="mt-4 flex items-center gap-2 text-red-400">
                      <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
                      <span className="font-mono font-bold text-lg">{fmt(elapsed)}</span>
                      <span className="text-xs text-gray-500">recording</span>
                    </div>
                  )}
                  {phase === STATES.PROCESSING && (
                    <div className="mt-4 flex items-center gap-2 text-indigo-400">
                      <Spinner size="sm" />
                      <span className="text-sm">Analysing your answer…</span>
                    </div>
                  )}
                    </div>
                  </div>

                  {/* Auto-skip notification */}
                  <AnimatePresence>
                  {autoSkipAlert && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="glass rounded-xl px-5 py-3 border border-amber-500/20 bg-amber-500/5 mb-4"
                    >
                      <p className="text-amber-400 text-sm">No response detected. Moving to next question...</p>
                    </motion.div>
                  )}
                  </AnimatePresence>

                  {/* Mic permission error */}
                  {permError && (
                    <div className="glass rounded-xl px-5 py-3 border border-red-500/20 bg-red-500/5 mb-4">
                      <p className="text-red-400 text-sm">Warning: {permError}</p>
                    </div>
                  )}

                  {/* Previous answer feedback (shown briefly on question state) */}
                  {phase === STATES.QUESTION && lastFeedback && roundNumber > 1 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      className={`glass rounded-2xl p-5 mb-5 border ${
                        isFollowUp
                          ? 'border-amber-500/20 bg-amber-500/[0.03]'
                          : 'border-white/5'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <p className="metric-label">Previous Answer Feedback</p>
                          {isFollowUp && (
                            <span className="text-[10px] text-amber-400/80 font-medium">
                              — AI is probing deeper
                            </span>
                          )}
                        </div>
                        {lastScore !== null && (
                          <span className={`font-bold text-lg ${scoreColour(lastScore)}`}>
                            {lastScore}/10
                          </span>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm leading-relaxed">{lastFeedback}</p>
                      {followUpReason && (
                        <p className="text-amber-400/70 text-xs mt-2 flex items-center gap-1">
                          <svg className="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 16v-4M12 8h.01" />
                          </svg>
                          {followUpReason}
                        </p>
                      )}
                    </motion.div>
                  )}

                  {phase === STATES.QUESTION && questionType === 'coding' && (
                    <div className="mb-6">
                      <CodeEditor onSubmitCode={submitCode} />
                    </div>
                  )}

                  {phase === STATES.QUESTION && questionType !== 'coding' && (
                    <div className="flex flex-wrap gap-3">
                      <motion.button
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                        onClick={handleStartRecording}
                        className="flex-1 py-4 rounded-2xl font-bold text-lg text-white
                                  bg-gradient-to-r from-red-600 to-rose-500
                                  hover:from-red-500 hover:to-rose-400
                                  shadow-xl shadow-red-500/20 transition-all"
                      >
                        Start Answering
                      </motion.button>

                      <motion.button
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                        onClick={skip}
                        title="Skip this question"
                        className="px-5 py-4 rounded-2xl font-semibold text-sm text-gray-400
                                  glass border border-white/10
                                  hover:border-white/20 hover:text-gray-200 transition-all"
                      >
                        Skip
                      </motion.button>

                      <motion.button
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                        onClick={handleEndInterview}
                        className="px-5 py-4 rounded-2xl font-semibold text-sm text-gray-300
                                  border border-red-500/25 bg-red-500/10
                                  hover:bg-red-500/20 transition-all"
                      >
                        End Interview
                      </motion.button>
                    </div>
                  )}
                </div>
                {/* Right section: camera preview in normal layout flow */}
                <div className="w-full lg:w-64 flex-shrink-0">
                  <WebcamPreview className="w-full h-48 rounded-xl shadow-lg bg-black overflow-hidden" />
                </div>
              </div>

              {phase === STATES.RECORDING && questionType !== 'coding' && (
                <div className="flex flex-wrap gap-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                    onClick={handleStopRecording}
                    className="flex-1 py-4 rounded-2xl font-bold text-lg text-white
                               bg-gradient-to-r from-indigo-600 to-purple-600
                               hover:from-indigo-500 hover:to-purple-500
                               shadow-xl shadow-indigo-500/20 transition-all"
                  >
                    Submit Answer
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                    onClick={skip}
                    title="Skip this question"
                    className="px-5 py-4 rounded-2xl font-semibold text-sm text-gray-400
                               glass border border-white/10
                               hover:border-white/20 hover:text-gray-200 transition-all"
                  >
                    Skip
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                    onClick={handleEndInterview}
                    className="px-5 py-4 rounded-2xl font-semibold text-sm text-gray-300
                               border border-red-500/25 bg-red-500/10
                               hover:bg-red-500/20 transition-all"
                  >
                    End Interview
                  </motion.button>
                </div>
              )}

              {phase === STATES.PROCESSING && (
                <div className="w-full py-4 rounded-2xl flex items-center justify-center gap-3
                                glass text-gray-500 font-semibold">
                  <Spinner size="sm" />
                  {isFinalizingLastAnswer ? 'Processing your final answer...' : 'AI is thinking...'}
                </div>
              )}
            </motion.div>
          )}

          {/* ── COMPLETE ─────────────────────────────────────────────── */}
          {phase === STATES.COMPLETE && finalResult && (
            <motion.div key="complete" {...fu(0)} className="max-w-lg mx-auto">
              <div className="flex justify-center mb-6">
                <Badge variant="success">Interview Complete</Badge>
              </div>
              <h2 className="text-4xl font-black text-center mb-2">
                Great job, <span className="gradient-text">well done!</span>
              </h2>
              <p className="text-gray-500 text-center text-sm mb-8">
                {(finalResult.question_reviews?.length ?? 0)} round{(finalResult.question_reviews?.length ?? 0) !== 1 ? 's' : ''} completed
              </p>

              <div className="glass rounded-2xl p-5 mb-4">
                <p className="metric-label mb-2">Final Score</p>
                <p className="text-4xl font-black gradient-text mb-2">{finalResult.final_score ?? 0}/10</p>
                <AnimatedBar value={(finalResult.final_score ?? 0) * 10} colorClass="from-indigo-500 to-purple-500" delay={0.3} />
              </div>

              {/* Summary */}
              <div className="glass rounded-2xl p-5 mb-4">
                <p className="metric-label mb-2">Summary</p>
                <p className="text-gray-300 text-sm leading-relaxed">{finalResult.summary}</p>
              </div>

              {!!finalResult.question_reviews?.length && (
                <div className="glass rounded-xl p-4 mb-8">
                  <p className="metric-label mb-3">Per-Question Learning Review</p>
                  <div className="space-y-4">
                    {finalResult.question_reviews.map((item, idx) => (
                      <div key={idx} className="border border-white/10 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Question {idx + 1}</p>
                        <p className="text-sm text-white mb-2">{item.question}</p>
                        <p className="text-xs text-gray-300 mb-1"><span className="text-gray-500">Your Answer:</span> {item.user_answer}</p>
                        {item.user_answer === 'SKIPPED' && (
                          <p className="text-xs text-amber-300 mb-2">You skipped this question. Here's how to answer it.</p>
                        )}
                        <p className="text-xs text-green-300 mb-1"><span className="text-gray-500">Score:</span> {item.score}/10</p>
                        <p className="text-xs text-gray-300 mb-1"><span className="text-gray-500">Feedback:</span> {item.feedback}</p>
                        <p className="text-xs text-indigo-300 mb-1"><span className="text-gray-500">Expected Answer:</span> {item.expected_answer}</p>
                        <p className="text-xs text-sky-300 mb-1"><span className="text-gray-500">Explanation:</span> {item.explanation}</p>
                        <p className="text-xs text-emerald-300 mb-1"><span className="text-gray-500">How to Answer:</span> {item.how_to_answer}</p>
                        {!!item.key_points?.length && (
                          <ul className="text-xs text-gray-300 mb-1 list-disc pl-4">
                            {item.key_points.map((kp, i) => <li key={i}>{kp}</li>)}
                          </ul>
                        )}
                        <p className="text-xs text-amber-300"><span className="text-gray-500">Example:</span> {item.example}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={reset}
                  className="flex-1 py-4 rounded-2xl font-bold text-lg text-white
                             bg-gradient-to-r from-purple-600 to-indigo-600
                             hover:from-purple-500 hover:to-indigo-500
                             shadow-xl transition-all"
                >
                  Practice Again →
                </button>
                <button
                  onClick={() => navigate('/')}
                  className="btn-ghost px-6 py-4 text-base"
                >
                  Home
                </button>
              </div>
            </motion.div>
          )}

          {/* ── ERROR ────────────────────────────────────────────────── */}
          {phase === STATES.ERROR && (
            <motion.div key="error" {...fu(0)} className="max-w-md mx-auto text-center py-20">
              <div className="text-6xl mb-6">!</div>
              <h2 className="text-2xl font-bold text-white mb-3">Something went wrong</h2>
              <p className="text-red-400 text-sm mb-8 glass rounded-xl px-5 py-3">
                {error}
              </p>
              <div className="flex gap-3 justify-center">
                <button onClick={reset} className="btn-primary">Try Again</button>
                <button onClick={() => navigate('/')} className="btn-ghost">Home</button>
              </div>
            </motion.div>
          )}

          </AnimatePresence>
        </div>
      </div>
    </PageWrapper>
  )
}
