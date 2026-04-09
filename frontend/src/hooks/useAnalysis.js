import { useState, useCallback } from 'react'
import { analyzeVideo } from '../services/api.js'

/**
 * useAnalysis
 * -----------
 * Encapsulates all state and logic for a single video analysis request.
 * Components just call `analyze(file)` and read `isLoading / result / error`.
 *
 * @returns {{
 *   analyze:    (file: File) => Promise<object>,
 *   isLoading:  boolean,
 *   progress:   number,        // 0–100 upload progress percent
 *   result:     object | null, // AnalysisResult from the API
 *   error:      string | null,
 *   reset:      () => void,
 * }}
 */
export function useAnalysis() {
  const [isLoading, setIsLoading] = useState(false)
  const [progress,  setProgress]  = useState(0)
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState(null)

  const analyze = useCallback(async (file) => {
    setIsLoading(true)
    setProgress(0)
    setError(null)
    setResult(null)

    try {
      const data = await analyzeVideo(file, setProgress)
      setResult(data)
      return data
    } catch (err) {
      const msg = err?.message ?? 'Analysis failed. Please try again.'
      setError(msg)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setIsLoading(false)
    setProgress(0)
    setResult(null)
    setError(null)
  }, [])

  return { analyze, isLoading, progress, result, error, reset }
}
