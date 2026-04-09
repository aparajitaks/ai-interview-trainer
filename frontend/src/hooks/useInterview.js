import { useState, useEffect, useRef, useCallback } from 'react'
import { startInterview, submitAnswer, submitCodeAnswer, skipQuestion, endInterview } from '../services/interviewApi.js'

export const STATES = {
  IDLE: 'idle',
  STARTING: 'starting',
  QUESTION: 'question',
  RECORDING: 'recording',
  PROCESSING: 'processing',
  COMPLETE: 'complete',
  ERROR: 'error',
}

export function useInterview() {
  const [phase, setPhase] = useState(STATES.IDLE)
  const [sessionId, setSessionId] = useState(null)
  const [role, setRole] = useState('Software Engineer')
  const [question, setQuestion] = useState('')
  const [questionType, setQuestionType] = useState('text')
  const [roundNumber, setRoundNumber] = useState(0)
  const [totalRounds, setTotalRounds] = useState(5)
  const [lastTranscript, setLastTranscript] = useState('')
  const [lastFeedback, setLastFeedback] = useState('')
  const [lastScore, setLastScore] = useState(null)
  const [lastExpectedAnswer, setLastExpectedAnswer] = useState('')
  const [lastGapAnalysis, setLastGapAnalysis] = useState('')
  const [lastImprovementSuggestion, setLastImprovementSuggestion] = useState('')
  const [finalResult, setFinalResult] = useState(null)
  const [error, setError] = useState('')
  const [isFinalizingLastAnswer, setIsFinalizingLastAnswer] = useState(false)
  const [isFollowUp, setIsFollowUp] = useState(false)
  const [followUpReason, setFollowUpReason] = useState(null)

  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef(null)

  const startTimer = () => {
    setElapsed(0)
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
  }
  const stopTimer = () => {
    clearInterval(timerRef.current)
    timerRef.current = null
  }
  const resetTimer = () => {
    stopTimer()
    setElapsed(0)
  }

  useEffect(() => () => clearInterval(timerRef.current), [])

  useEffect(() => {
    if (!question) return
    // New question loaded: always clear finalizing state.
    setIsFinalizingLastAnswer(false)
  }, [question])

  const begin = useCallback(
    async (selectedRole = role, rounds = 5) => {
      setPhase(STATES.STARTING)
      setError('')
      setFinalResult(null)
      try {
        const data = await startInterview({ role: selectedRole, maxRounds: rounds })
        setSessionId(data.session_id)
        setRole(selectedRole)
        setQuestion(data.question)
        setQuestionType(data.type || 'text')
        setRoundNumber(data.round_number)
        setTotalRounds(data.total_rounds)
        setPhase(STATES.QUESTION)
      } catch (err) {
        setError(err.message)
        setPhase(STATES.ERROR)
      }
    },
    [role]
  )

  const onRecordingStarted = useCallback(() => {
    setPhase(STATES.RECORDING)
    startTimer()
  }, [])

  const submitAudio = useCallback(
    async (audioBlob) => {
      stopTimer()
      setPhase(STATES.PROCESSING)
      setLastTranscript('')
      setLastFeedback('')
      setLastScore(null)
      setLastExpectedAnswer('')
      setLastGapAnalysis('')
      setLastImprovementSuggestion('')
      setIsFinalizingLastAnswer(false)

      try {
        const data = await submitAnswer({ sessionId, audioBlob })
        console.log('[submitAudio] response:', {
          round_number: data.round_number,
          total_rounds: data.total_rounds,
          is_last: data.is_last,
          is_complete: data.is_complete,
        })
        setLastTranscript(data.transcript)
        setLastFeedback(data.feedback)
        setLastScore(data.score)
        setLastExpectedAnswer(data.expected_answer || '')
        setLastGapAnalysis(data.gap_analysis || '')
        setLastImprovementSuggestion(data.improvement_suggestion || '')
        setIsFollowUp(data.follow_up || data.is_follow_up || false)
        setFollowUpReason(data.follow_up_reason || null)

        if (data.is_last) {
          setIsFinalizingLastAnswer(true)
          const final = await endInterview(sessionId)
          setFinalResult(final)
          setIsFinalizingLastAnswer(false)
          setPhase(STATES.COMPLETE)
        } else {
          setQuestion(data.next_question)
          setQuestionType(data.type || 'text')
          setRoundNumber(data.round_number + 1)
          resetTimer()
          setPhase(STATES.QUESTION)
        }
      } catch (err) {
        setIsFinalizingLastAnswer(false)
        setError(err.message)
        setPhase(STATES.ERROR)
      }
    },
    [sessionId]
  )

  const skip = useCallback(async () => {
    stopTimer()
    if (!sessionId) return
    setPhase(STATES.PROCESSING)
    setError('')
    try {
      const data = await skipQuestion(sessionId)
      if (data.is_complete) {
        const final = await endInterview(sessionId)
        setFinalResult(final)
        setPhase(STATES.COMPLETE)
      } else {
        setQuestion(data.next_question)
        setQuestionType('text')
        setRoundNumber(data.round_number + 1)
        resetTimer()
        setPhase(STATES.QUESTION)
      }
    } catch (err) {
      setError(err.message)
      setPhase(STATES.ERROR)
    }
  }, [sessionId])

  const quit = useCallback(async () => {
    stopTimer()
    if (!sessionId) {
      setPhase(STATES.IDLE)
      return
    }
    try {
      const final = await endInterview(sessionId)
      setFinalResult(final)
      setPhase(STATES.COMPLETE)
    } catch {
      setPhase(STATES.IDLE)
    }
  }, [sessionId])

  const reset = useCallback(() => {
    resetTimer()
    setPhase(STATES.IDLE)
    setSessionId(null)
    setQuestion('')
    setQuestionType('text')
    setRoundNumber(0)
    setLastTranscript('')
    setLastFeedback('')
    setLastScore(null)
    setLastExpectedAnswer('')
    setLastGapAnalysis('')
    setLastImprovementSuggestion('')
    setIsFinalizingLastAnswer(false)
    setFinalResult(null)
    setError('')
    setIsFollowUp(false)
    setFollowUpReason(null)
  }, [])

  const submitCode = useCallback(
    async (codeAnswer) => {
      stopTimer()
      setPhase(STATES.PROCESSING)
      setLastTranscript('')
      setLastFeedback('')
      setLastScore(null)
      setLastExpectedAnswer('')
      setLastGapAnalysis('')
      setLastImprovementSuggestion('')
      setIsFinalizingLastAnswer(false)

      try {
        const data = await submitCodeAnswer({ sessionId, answer: codeAnswer })
        console.log('[submitCode] response:', {
          round_number: data.round_number,
          total_rounds: data.total_rounds,
          is_last: data.is_last,
          is_complete: data.is_complete,
        })
        setLastTranscript(data.transcript)
        setLastFeedback(data.feedback)
        setLastScore(data.score)
        setLastExpectedAnswer(data.expected_answer || '')
        setLastGapAnalysis(data.gap_analysis || '')
        setLastImprovementSuggestion(data.improvement_suggestion || '')
        setIsFollowUp(data.follow_up || data.is_follow_up || false)
        setFollowUpReason(data.follow_up_reason || null)

        if (data.is_last) {
          setIsFinalizingLastAnswer(true)
          const final = await endInterview(sessionId)
          setFinalResult(final)
          setIsFinalizingLastAnswer(false)
          setPhase(STATES.COMPLETE)
        } else {
          setQuestion(data.next_question)
          setQuestionType(data.type || 'text')
          setRoundNumber(data.round_number + 1)
          resetTimer()
          setPhase(STATES.QUESTION)
        }
      } catch (err) {
        setIsFinalizingLastAnswer(false)
        setError(err.message)
        setPhase(STATES.ERROR)
      }
    },
    [sessionId]
  )

  return {
    phase,
    sessionId,
    role,
    setRole,
    question,
    questionType,
    roundNumber,
    totalRounds,
    lastTranscript,
    lastFeedback,
    lastScore,
    lastExpectedAnswer,
    lastGapAnalysis,
    lastImprovementSuggestion,
    finalResult,
    error,
    isFinalizingLastAnswer,
    elapsed,
    isFollowUp,
    followUpReason,
    begin,
    onRecordingStarted,
    submitAudio,
    submitCode,
    skip,
    quit,
    reset,
  }
}
