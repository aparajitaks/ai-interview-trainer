import { motion } from 'framer-motion'

/**
 * PageWrapper
 * -----------
 * Wraps every page with a consistent fade-up enter / fade-down exit animation.
 * Used by all three pages so navigation always feels smooth.
 */
export default function PageWrapper({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{    opacity: 0, y: -8 }}
      transition={{ duration: 0.28, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  )
}
