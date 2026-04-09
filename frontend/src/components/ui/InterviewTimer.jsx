import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * InterviewTimer
 * --------------
 * 30-minute countdown timer with color transitions and auto-end.
 *
 * Props
 * -----
 *  durationMinutes : number  — total duration (default 30)
 *  isRunning       : bool    — controls whether the timer ticks
 *  onTimeUp        : () => void — called when timer reaches 0
 */

const fmt = (totalSecs) => {
  const m = Math.floor(totalSecs / 60)
  const s = totalSecs % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function InterviewTimer({
  durationMinutes = 30,
  isRunning = true,
  onTimeUp,
}) {
  const [remaining, setRemaining] = useState(durationMinutes * 60)
  const intervalRef = useRef(null)
  const onTimeUpRef = useRef(onTimeUp)

  // Keep callback ref fresh without re-triggering effects
  useEffect(() => { onTimeUpRef.current = onTimeUp }, [onTimeUp])

  useEffect(() => {
    if (!isRunning) {
      clearInterval(intervalRef.current)
      return
    }

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current)
          onTimeUpRef.current?.()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(intervalRef.current)
  }, [isRunning])

  // Colour transitions based on remaining time
  const pct = remaining / (durationMinutes * 60)
  let colorClass = 'text-white/70'
  let ringColor  = 'border-white/10'

  if (pct <= 0.033) {
    // < 1 minute — red + pulse
    colorClass = 'text-red-400 animate-pulse'
    ringColor  = 'border-red-500/40'
  } else if (pct <= 0.167) {
    // < 5 minutes — yellow
    colorClass = 'text-amber-400'
    ringColor  = 'border-amber-500/30'
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${ringColor}
                     bg-white/[0.03] transition-colors duration-500`}>
      <svg className="w-3.5 h-3.5 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span className={`font-mono font-bold text-sm tabular-nums ${colorClass} transition-colors duration-500`}>
        {fmt(remaining)}
      </span>
    </div>
  )
}
