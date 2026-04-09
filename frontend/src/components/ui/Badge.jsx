/**
 * Badge
 * -----
 * Pill-shaped status badge used in hero and results sections.
 * variant: 'live' | 'success' | 'warning'
 */
const VARIANTS = {
    live:    'border-indigo-500/20 text-indigo-300',
    success: 'border-green-500/20  text-green-300',
    warning: 'border-yellow-500/20 text-yellow-300',
  }
  
  const DOTS = {
    live:    'bg-green-400 animate-pulse',
    success: 'bg-green-400',
    warning: 'bg-yellow-400',
  }
  
  export default function Badge({ children, variant = 'live' }) {
    return (
      <div className={`
        inline-flex items-center gap-2
        glass px-4 py-1.5 rounded-full
        border text-sm font-medium
        ${VARIANTS[variant]}
      `}>
        <span className={`w-1.5 h-1.5 rounded-full ${DOTS[variant]}`} />
        {children}
      </div>
    )
  }
  