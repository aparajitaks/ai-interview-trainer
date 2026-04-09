import { useState } from 'react'
import Editor from '@monaco-editor/react'
import Spinner from './ui/Spinner.jsx'
import { runCode } from '../services/interviewApi.js'

export default function CodeEditor({ onSubmitCode }) {
  const [code, setCode] = useState('def solve():\n    # write your solution\n    pass\n')
  const [stdin, setStdin] = useState('')
  const [output, setOutput] = useState('')
  const [error, setError] = useState('')
  const [isRunning, setIsRunning] = useState(false)

  const handleRun = async () => {
    setIsRunning(true)
    setError('')
    setOutput('')
    try {
      const res = await runCode({ code, input: stdin })
      setOutput(res.output || '(no output)')
      setError(res.error || '')
    } catch (err) {
      setError(err.message || 'Run failed')
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="glass rounded-2xl p-4 space-y-4">
      <Editor
        height="360px"
        defaultLanguage="python"
        value={code}
        theme="vs-dark"
        onChange={(v) => setCode(v || '')}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          automaticLayout: true,
        }}
      />

      <div>
        <label className="metric-label block mb-2">Input (stdin, optional)</label>
        <textarea
          value={stdin}
          onChange={(e) => setStdin(e.target.value)}
          rows={4}
          className="w-full rounded-xl bg-black/30 border border-white/10 p-3 text-sm text-gray-200"
          placeholder="Provide input for your program..."
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleRun}
          disabled={isRunning || !code.trim()}
          className="btn-primary px-5 py-2.5 text-sm disabled:opacity-50"
        >
          {isRunning ? (
            <span className="inline-flex items-center gap-2"><Spinner size="sm" /> Running...</span>
          ) : (
            'Run Code'
          )}
        </button>
        <button
          onClick={() => onSubmitCode(code)}
          disabled={!code.trim() || isRunning}
          className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50"
        >
          Submit Answer
        </button>
      </div>

      <div className="rounded-xl bg-black/40 border border-white/10 p-3">
        <p className="metric-label mb-2">Output</p>
        {error ? (
          <pre className="text-sm whitespace-pre-wrap text-red-400">{error}</pre>
        ) : (
          <pre className="text-sm whitespace-pre-wrap text-gray-200">{output || 'Run your code to see output.'}</pre>
        )}
      </div>
    </div>
  )
}

