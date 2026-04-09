/**
 * Spinner
 * -------
 * Animated loading indicator using a dual-ring CSS approach.
 * Size variants: sm | md | lg | xl
 */
const SIZES = {
    sm:  'w-5  h-5  border-2',
    md:  'w-8  h-8  border-2',
    lg:  'w-12 h-12 border-[3px]',
    xl:  'w-16 h-16 border-4',
  }
  
  export default function Spinner({ size = 'md', className = '' }) {
    const ring = SIZES[size] ?? SIZES.md
    return (
      <span
        role="status"
        aria-label="Loading"
        className={`
          inline-block rounded-full animate-spin
          border-indigo-500/20 border-t-indigo-500
          ${ring} ${className}
        `}
      />
    )
  }
  