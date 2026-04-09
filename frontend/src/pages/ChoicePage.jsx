import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PageWrapper from '../layouts/PageWrapper.jsx'
import Badge from '../components/ui/Badge.jsx'

export default function ChoicePage() {
  const navigate = useNavigate()

  return (
    <PageWrapper>
      <div className="min-h-screen bg-[#0A0F1E] px-4 py-16 overflow-x-hidden">
        <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-purple-800/10 rounded-full blur-[120px]" />
          <div className="absolute top-2/3 -right-40 w-[500px] h-[500px] bg-indigo-800/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-xl mx-auto text-center">
          <Badge variant="live">Choose Interview Mode</Badge>

          <h1 className="text-5xl font-black tracking-tight mt-6 mb-3">
            Start Your <span className="gradient-text">Interview</span>
          </h1>
          <p className="text-gray-400 mb-10">
            Pick how you want to practice today.
          </p>

          <div className="flex flex-col gap-4">
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/upload')}
              className="w-full py-4 rounded-2xl font-bold text-lg text-white
                         bg-gradient-to-r from-indigo-600 to-purple-600
                         hover:from-indigo-500 hover:to-purple-500
                         shadow-xl shadow-indigo-500/20 transition-all"
            >
              Upload Video →
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/live')}
              className="w-full py-4 rounded-2xl font-bold text-lg text-white
                         bg-gradient-to-r from-purple-700 to-rose-600
                         hover:from-purple-600 hover:to-rose-500
                         shadow-xl shadow-purple-500/20 transition-all"
            >
              Live Interview →
            </motion.button>
          </div>
        </div>
      </div>
    </PageWrapper>
  )
}
