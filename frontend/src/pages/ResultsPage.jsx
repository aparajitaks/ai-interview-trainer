import { useEffect }            from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion }               from 'framer-motion'
import PageWrapper              from '../layouts/PageWrapper.jsx'
import AnimatedBar              from '../components/ui/AnimatedBar.jsx'
import Badge                    from '../components/ui/Badge.jsx'

/* ── Emotion config ─────────────────────────────────────────────────────── */
const EMOTIONS = {
  Happy:    { emoji: '😊', label: 'Happy',    color: 'text-yellow-300',  bar: 'from-yellow-400 to-amber-400',  bg: 'bg-yellow-500/10', border: 'border-yellow-500/15' },
  Neutral:  { emoji: '😐', label: 'Neutral',  color: 'text-blue-300',    bar: 'from-blue-400   to-indigo-400',  bg: 'bg-blue-500/10',   border: 'border-blue-500/15'   },
  Sad:      { emoji: '😔', label: 'Sad',      color: 'text-indigo-300',  bar: 'from-indigo-400 to-blue-400',   bg: 'bg-indigo-500/10', border: 'border-indigo-500/15' },
  Angry:    { emoji: '😠', label: 'Angry',    color: 'text-red-300',     bar: 'from-red-400    to-rose-400',   bg: 'bg-red-500/10',    border: 'border-red-500/15'    },
  Surprise: { emoji: '😲', label: 'Surprise', color: 'text-purple-300',  bar: 'from-purple-400 to-violet-400', bg: 'bg-purple-500/10', border: 'border-purple-500/15' },
}

/* ── Posture config ─────────────────────────────────────────────────────── */
const POSTURES = {
  Good:      { icon: '✅', label: 'Good',      subtext: 'Keep it up — confident body language.',  color: 'text-green-400',  border: 'border-green-500/15'  },
  Slouching: { icon: '⚠️', label: 'Slouching', subtext: 'Straighten your back for a better impression.', color: 'text-yellow-400', border: 'border-yellow-500/15' },
  Leaning:   { icon: '↗️', label: 'Leaning',   subtext: 'Try sitting squarely in front of the camera.',  color: 'text-orange-400', border: 'border-orange-500/15' },
  Unknown:   { icon: '❓', label: 'Unknown',   subtext: 'Could not detect your pose clearly.',   color: 'text-gray-400',   border: 'border-white/10'      },
}

/* ── Eye-contact colour helper ──────────────────────────────────────────── */
function eyeStyle(pct) {
  if (pct >= 65) return { color: 'text-green-300',  bar: 'from-green-400 to-emerald-400', tip: 'Excellent — strong direct camera gaze.' }
  if (pct >= 35) return { color: 'text-yellow-300', bar: 'from-yellow-400 to-amber-400',  tip: 'Moderate — try to look at the camera more.'   }
  return              { color: 'text-red-300',    bar: 'from-red-400   to-rose-400',    tip: 'Low — practice maintaining eye contact.'     }
}

/* ── Confidence colour helper ───────────────────────────────────────────── */
function confStyle(score) {
  if (score >= 75) return { bar: 'from-green-500  to-emerald-400', grade: 'Excellent' }
  if (score >= 50) return { bar: 'from-yellow-500 to-amber-400',  grade: 'Good'      }
  return               { bar: 'from-red-500    to-orange-400', grade: 'Needs Work' }
}

/* ── Card fade-up animation ─────────────────────────────────────────────── */
const card = (delay = 0) => ({
  initial:    { opacity: 0, y: 20 },
  animate:    { opacity: 1, y: 0  },
  transition: { delay, duration: 0.45, ease: 'easeOut' },
})

/* ═══════════════════════════════════════════════════════════════════════════
   ResultsPage
   ════════════════════════════════════════════════════════════════════════ */
export default function ResultsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const result   = location.state?.result

  /* Redirect if no result (e.g., direct URL access) */
  useEffect(() => {
    if (!result) navigate('/upload', { replace: true })
  }, [result, navigate])

  if (!result) return null

  const emo  = EMOTIONS[result.emotion]  ?? EMOTIONS.Neutral
  const pst  = POSTURES[result.posture]  ?? POSTURES.Unknown
  const eye  = eyeStyle(result.eye_contact)
  const conf = confStyle(result.confidence_score)

  return (
    <PageWrapper>
      <div className="min-h-screen bg-[#0A0F1E] px-4 py-20">

        {/* Ambient orbs */}
        <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4  w-[700px] h-[700px] bg-indigo-900/12 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-2xl mx-auto">

          {/* ── Header ────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0   }}
            transition={{ duration: 0.4 }}
            className="text-center mb-10"
          >
            <div className="flex justify-center mb-5">
              <Badge variant="success">Analysis Complete</Badge>
            </div>

            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-3">
              Your Interview{' '}
              <span className="gradient-text">Feedback</span>
            </h1>
            <p className="text-gray-500 text-sm">
              Based on{' '}
              <span className="text-gray-300">{result.frames_processed}</span>{' '}
              frames sampled ·{' '}
              <span className="text-gray-300">{result.frames_with_face}</span>{' '}
              frames with face detected
            </p>
          </motion.div>

          {/* ── Top two cards in a grid ──────────────────────────────── */}
          <div className="grid grid-cols-2 gap-4 mb-4">

            {/* Emotion card */}
            <motion.div
              {...card(0.1)}
              className={`glass rounded-2xl p-6 border ${emo.border}`}
            >
              <p className="metric-label mb-4">Emotion</p>
              <div className={`w-14 h-14 rounded-2xl ${emo.bg} flex items-center justify-center text-3xl mb-4`}>
                {emo.emoji}
              </div>
              <p className={`text-2xl font-black ${emo.color}`}>{emo.label}</p>
              <AnimatedBar
                value={100}
                colorClass={emo.bar}
                delay={0.7}
                className="mt-3"
              />
            </motion.div>

            {/* Eye contact card */}
            <motion.div
              {...card(0.2)}
              className="glass rounded-2xl p-6 border border-cyan-500/10"
            >
              <p className="metric-label mb-4">Eye Contact</p>
              <p className={`text-5xl font-black ${eye.color} leading-none mb-1`}>
                {result.eye_contact}
                <span className="text-2xl font-semibold opacity-60">%</span>
              </p>
              <AnimatedBar
                value={result.eye_contact}
                colorClass={eye.bar}
                delay={0.75}
                className="mt-4"
              />
              <p className="text-gray-500 text-xs mt-2 leading-snug">{eye.tip}</p>
            </motion.div>
          </div>

          {/* ── Posture card (full width) ─────────────────────────────── */}
          <motion.div
            {...card(0.3)}
            className={`glass rounded-2xl p-6 mb-4 border ${pst.border}`}
          >
            <p className="metric-label mb-4">Posture</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-4xl">{pst.icon}</span>
                <div>
                  <p className={`text-2xl font-black ${pst.color}`}>{pst.label}</p>
                  <p className="text-gray-500 text-sm mt-0.5">{pst.subtext}</p>
                </div>
              </div>
              <div className="glass rounded-xl px-4 py-2.5 text-right shrink-0">
                <p className="text-[10px] text-gray-600 uppercase tracking-wider">Body Language</p>
                <p className={`text-base font-bold mt-0.5 ${pst.color}`}>
                  {result.posture === 'Good' ? 'Confident' : 'Adjust'}
                </p>
              </div>
            </div>
          </motion.div>

          {/* ── Confidence score (full width) ─────────────────────────── */}
          <motion.div
            {...card(0.4)}
            className="glass rounded-2xl p-6 mb-8 border border-white/[0.06]"
          >
            <div className="flex items-center justify-between mb-5">
              <div>
                <p className="metric-label mb-1">Overall Confidence Score</p>
                <p className="text-gray-500 text-xs">
                  Weighted: 40% face detection · 30% eye contact · 30% posture
                </p>
              </div>
              <motion.span
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1   }}
                transition={{ delay: 0.9, type: 'spring', stiffness: 200 }}
                className={`text-4xl font-black bg-gradient-to-r ${conf.bar} bg-clip-text text-transparent`}
              >
                {result.confidence_score}
              </motion.span>
            </div>

            <AnimatedBar
              value={result.confidence_score}
              colorClass={conf.bar}
              delay={0.85}
              className="mb-3"
            />

            <div className="flex justify-between text-[10px] text-gray-700 font-medium">
              <span>Needs Work</span>
              <span className={`font-bold ${conf.bar.includes('green') ? 'text-green-500' : conf.bar.includes('yellow') ? 'text-yellow-500' : 'text-red-500'}`}>
                {conf.grade}
              </span>
              <span>Excellent</span>
            </div>
          </motion.div>

          {/* ── Actions ───────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.65 }}
            className="flex gap-3"
          >
            <button
              onClick={() => navigate('/upload')}
              className="flex-1 py-4 rounded-2xl font-bold text-lg text-white
                         bg-gradient-to-r from-indigo-600 to-purple-600
                         hover:from-indigo-500 hover:to-purple-500
                         shadow-xl shadow-indigo-500/20
                         active:scale-[0.98] transition-all duration-200"
            >
              Analyse Another →
            </button>
            <button
              onClick={() => navigate('/')}
              className="btn-ghost px-6 py-4 text-base"
            >
              Home
            </button>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  )
}
