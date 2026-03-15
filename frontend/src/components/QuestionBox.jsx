import React from 'react'

export default function QuestionBox() {
  return (
    <div className="h-full bg-gray-800 rounded-xl p-6 shadow-lg flex flex-col justify-between">
      <div>
        <h3 className="text-2xl font-semibold">Tell me about yourself</h3>
        <p className="text-gray-300 mt-4 leading-relaxed">Give a brief summary of your background, strengths, and interests relevant to this role. Focus on experience, key accomplishments, and what drives you.</p>
      </div>

      <div className="flex items-center justify-end">
        <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-full text-white font-medium">Next Question</button>
      </div>
    </div>
  )
}
