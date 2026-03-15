import React from 'react'

export default function QuestionBox() {
  return (
    <div className="bg-gray-800 rounded-lg p-6 h-full flex flex-col justify-between">
      <div>
        <h3 className="text-xl font-semibold">Current Question</h3>
        <p className="text-gray-300 mt-3">Tell me about a time you faced a challenge at work. How did you handle it?</p>
      </div>

      <div className="text-right">
        <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-full text-white">Next Question</button>
      </div>
    </div>
  )
}
