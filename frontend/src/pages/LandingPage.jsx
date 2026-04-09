import { useNavigate } from 'react-router-dom'
import { motion }      from 'framer-motion'
import PageWrapper     from '../layouts/PageWrapper.jsx'
import Badge           from '../components/ui/Badge.jsx'

/* ── Feature cards data ─────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon:  '🧠',
    title: 'AI Interview Simulation',
    desc:  'Practice real interviews with dynamic, domain-specific questions and intelligent follow-ups.',
    color: 'group-hover:text-purple-400',
  },
  {
    icon:  '🎤',
    title: 'Answer Evaluation',
    desc:  'Get detailed analysis of your technical accuracy, clarity, and depth of understanding.',
    color: 'group-hover:text-cyan-400',
  },
  {
    icon:  '🤖',
    title: 'Smart Feedback',
    desc:  'Receive human-like feedback highlighting your strengths and areas for improvement.',
    color: 'group-hover:text-indigo-400',
  },
  {
    icon:  '📚',
    title: 'Learning Mode',
    desc:  'Even if you skip, learn the correct answers with explanations, gap analysis, and structured responses.',
    color: 'group-hover:text-emerald-400',
  },
  {
    icon:  '📊',
    title: 'Performance Insights',
    desc:  'Track your scores, identify weak areas, and monitor your progress over time.',
    color: 'group-hover:text-amber-400',
  },
  {
    icon:  '🎯',
    title: 'Improvement Plan',
    desc:  'Get a personalized roadmap with topics to study and practical steps to improve.',
    color: 'group-hover:text-rose-400',
  },
]

/* ── Stats row ──────────────────────────────────────────────────────────── */
const STATS = [
  { value: '< 30s', label: 'Analysis time' },
  { value: '5',     label: 'Emotion states' },
  { value: '100%',  label: 'Automatic' },
]

/* ── Animation helpers ──────────────────────────────────────────────────── */
const fadeUp = (delay = 0) => ({
  initial:    { opacity: 0, y: 24 },
  animate:    { opacity: 1, y: 0  },
  transition: { duration: 0.55, ease: 'easeOut', delay },
})

/* ═══════════════════════════════════════════════════════════════════════════
   LandingPage
   ════════════════════════════════════════════════════════════════════════ */
export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <PageWrapper>
      <div className="min-h-screen bg-[#0A0F1E] overflow-x-hidden">

        {/* ── Ambient glow orbs ───────────────────────────────────────── */}
        <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
          <div className="absolute -top-32 -left-32 w-[600px] h-[600px]
                          bg-indigo-600/10 rounded-full blur-[120px]" />
          <div className="absolute top-1/2 -right-48 w-[500px] h-[500px]
                          bg-purple-700/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px]
                          bg-cyan-800/8 rounded-full blur-[100px]" />
          {/* Subtle grid */}
          <div
            className="absolute inset-0 opacity-[0.025]"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,.15) 1px, transparent 1px),' +
                'linear-gradient(90deg, rgba(255,255,255,.15) 1px, transparent 1px)',
              backgroundSize: '48px 48px',
            }}
          />
        </div>

        {/* ── Navbar ──────────────────────────────────────────────────── */}
        <header className="relative z-10">
          <nav className="max-w-7xl mx-auto flex items-center justify-between px-6 py-5">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl select-none">🎯</span>
              <span className="font-black text-xl tracking-tight gradient-text">
                InterviewAI
              </span>
            </div>
            <button
              onClick={() => navigate('/choose')}
              className="btn-primary text-sm px-5 py-2.5"
            >
              Get Started
            </button>
          </nav>
        </header>

        {/* ── Hero ────────────────────────────────────────────────────── */}
        <main className="relative z-10 max-w-5xl mx-auto px-6 pt-20 pb-8 text-center">

          {/* Badge */}
          <motion.div className="flex justify-center mb-8" {...fadeUp(0)}>
            <Badge variant="live">AI-Powered Interview Analysis</Badge>
          </motion.div>

          {/* Headline */}
          <motion.h1
            className="text-6xl md:text-7xl lg:text-8xl font-black leading-[1.05] tracking-tight mb-6"
            {...fadeUp(0.1)}
          >
            <span className="text-white">Ace Your</span>
            <br />
            <span className="gradient-text">Next Interview</span>
          </motion.h1>

          {/* Sub */}
          <motion.p
            className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto leading-relaxed mb-10"
            {...fadeUp(0.2)}
          >
            Simulate real interviews. Improve with every answer. Our AI
            evaluates what you say, how you say it, and helps you refine your
            responses like a real interviewer would.
          </motion.p>

          {/* CTA */}
          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6"
            {...fadeUp(0.3)}
          >
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{  scale: 0.97 }}
              onClick={() => navigate('/choose')}
              className="px-9 py-4 rounded-2xl font-bold text-lg text-white
                         bg-gradient-to-r from-indigo-600 to-purple-600
                         hover:from-indigo-500 hover:to-purple-500
                         shadow-2xl shadow-indigo-500/30 transition-all duration-200"
            >
              Start Interview →
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{  scale: 0.97 }}
              onClick={() => navigate('/live')}
              className="px-9 py-4 rounded-2xl font-bold text-lg text-white
                         bg-gradient-to-r from-purple-700 to-rose-600
                         hover:from-purple-600 hover:to-rose-500
                         shadow-2xl shadow-purple-500/20 transition-all duration-200"
            >
              🎙️ Live Interview →
            </motion.button>
          </motion.div>

          <motion.p className="text-xs text-gray-600" {...fadeUp(0.35)}>
            No account needed · Free analysis · Results in under 30 seconds
          </motion.p>

          {/* Stats */}
          <motion.div
            className="flex items-center justify-center gap-10 mt-14 pt-10
                       border-t border-white/[0.06]"
            {...fadeUp(0.4)}
          >
            {STATS.map((s) => (
              <div key={s.label} className="text-center">
                <p className="text-3xl font-black gradient-text">{s.value}</p>
                <p className="text-xs text-gray-500 mt-1 font-medium">{s.label}</p>
              </div>
            ))}
          </motion.div>
        </main>

        {/* ── Feature cards ───────────────────────────────────────────── */}
        <section
          id="features"
          className="relative z-10 max-w-5xl mx-auto px-6 py-24"
        >
          <motion.p
            className="text-center metric-label mb-12"
            {...fadeUp(0)}
          >
            What InterviewAI Helps You Master
          </motion.p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                whileHover={{ y: -4 }}
                className="glass rounded-2xl p-7 group cursor-default
                           hover:border-indigo-500/20 transition-all duration-300"
              >
                <span className={`text-4xl block mb-5 transition-all duration-300 ${f.color}`}>
                  {f.icon}
                </span>
                <h3 className="text-white font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA strip ────────────────────────────────────────── */}
        <section className="relative z-10 max-w-5xl mx-auto px-6 pb-24">
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass rounded-3xl p-12 text-center
                       border-indigo-500/10 bg-gradient-to-b
                       from-indigo-500/[0.06] to-transparent"
          >
            <h2 className="text-4xl font-black text-white mb-4">
              Ready to improve?
            </h2>
            <p className="text-gray-400 mb-8 max-w-lg mx-auto">
              Upload a short clip from your next mock interview and let the AI
              show you exactly what to work on.
            </p>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/choose')}
              className="btn-primary px-10 py-4 text-base"
            >
              Start Interview →
            </motion.button>
          </motion.div>
        </section>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        <footer className="relative z-10 border-t border-white/[0.05] py-8">
          <p className="text-center text-xs text-gray-600">
            © 2026 InterviewAI · Built with MediaPipe + FastAPI + React
          </p>
        </footer>
      </div>
    </PageWrapper>
  )
}
