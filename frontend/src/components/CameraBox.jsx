import React from 'react'

export default function CameraBox() {
  return (
    <div className="w-full h-full bg-gray-800 rounded-xl shadow-lg flex items-center justify-center">
      <div className="w-full max-w-3xl p-6">
        <div className="bg-gray-900 rounded-lg aspect-video flex items-center justify-center border border-gray-700">
          <span className="text-gray-400 text-lg font-medium">Camera Preview</span>
        </div>
      </div>
    </div>
  )
}
