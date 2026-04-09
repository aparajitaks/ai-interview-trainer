import { motion } from 'framer-motion'

/**
 * AnimatedBar
 * -----------
 * Horizontally-animated progress bar that fills on mount.
 *
 * Props:
 *  value      {number} 0–100
 *  colorClass {string} Tailwind bg-gradient-to-r classes
 *  delay      {number} Framer motion delay in seconds
 */
export default function AnimatedBar({
  value = 0,
  colorClass = 'from-indigo-500 to-purple-500',
  delay = 0.5,
  className = '',
}) {
  const pct = Math.min(100, Math.max(0, value))

  return (
    <div className={`relative h-2.5 rounded-full bg-white/[0.06] overflow-hidden ${className}`}>
      <motion.div
        className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${colorClass}`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ delay, duration: 0.9, ease: [0.25, 0.46, 0.45, 0.94] }}
      />
    </div>
  )
}
