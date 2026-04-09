import { motion } from 'framer-motion'
import InterviewTimer from './InterviewTimer.jsx'

/**
 * ProgressHeader
 * --------------
 * Top-of-screen progress strip showing:
 *  - Animated gradient fill bar  (currentRound / totalRounds)
 *  - "Question X of Y" label
 *  - Countdown timer
 *
 * Props
 * -----
 *  roundNumber   : int   — current round (1-indexed)
 *  totalRounds   : int   — total rounds in the interview
 *  isTimerRunning: bool  — whether the countdown is active
 *  onTimeUp      : fn    — called when 30 min timer expires
 */

export default function ProgressHeader({
  roundNumber,
  totalRounds,
  isTimerRunning = true,
  onTimeUp,
}) {
  const progress = totalRounds > 0
    ? Math.min(100, ((roundNumber - 1) / totalRounds) * 100)
    : 0

  // Dynamic gradient hue shifts as you progress
  const hueStart = 240 + progress * 0.6   // indigo → purple
  const hueEnd   = 270 + progress * 0.4

  return (
    <div className="mb-6">
      {/* Top bar: question counter + timer */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                          bg-white/[0.04] border border-white/[0.08]">
            <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-500">
              Question
            </span>
            <span className="text-sm font-black text-white">
              {roundNumber}
              <span className="text-gray-600 font-medium"> / {totalRounds}</span>
            </span>
          </div>

          {/* Completion percentage pill */}
          <span className="text-[10px] font-semibold text-gray-600">
            {Math.round(progress)}% complete
          </span>
        </div>

        <InterviewTimer
          durationMinutes={30}
          isRunning={isTimerRunning}
          onTimeUp={onTimeUp}
        />
      </div>

      {/* Progress bar */}
      <div className="relative w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            background: `linear-gradient(90deg,
              hsl(${hueStart}, 70%, 55%),
              hsl(${hueEnd}, 80%, 60%))`,
          }}
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.6, ease: 'easeInOut' }}
        />
        {/* Glow effect on the leading edge */}
        <motion.div
          className="absolute inset-y-0 w-8 rounded-full blur-sm opacity-60"
          style={{
            background: `hsl(${hueEnd}, 80%, 65%)`,
          }}
          initial={{ left: '0%' }}
          animate={{ left: `calc(${progress}% - 16px)` }}
          transition={{ duration: 0.6, ease: 'easeInOut' }}
        />
      </div>

      {/* Round dots indicator */}
      <div className="flex gap-1.5 mt-2.5">
        {Array.from({ length: totalRounds }, (_, i) => {
          const isDone    = i < roundNumber - 1
          const isCurrent = i === roundNumber - 1
          return (
            <motion.div
              key={i}
              className={`h-1 rounded-full transition-all duration-500 ${
                isDone
                  ? 'bg-gradient-to-r from-indigo-500 to-purple-500'
                  : isCurrent
                    ? 'bg-purple-400'
                    : 'bg-white/[0.08]'
              }`}
              style={{ flex: 1 }}
              initial={false}
              animate={{
                opacity: isDone || isCurrent ? 1 : 0.5,
                scale: isCurrent ? 1 : 1,
              }}
            />
          )
        })}
      </div>
    </div>
  )
}
