import React from 'react'

export default function CameraBox() {
  return (
    <div className="h-full bg-gray-800 rounded-lg border-2 border-dashed border-gray-700 flex items-center justify-center">
      <div className="text-center text-gray-400">
        <div className="w-64 h-40 bg-gray-900 rounded-md"></div>
        <p className="mt-3">Camera preview (disabled)</p>
      </div>
    </div>
  )
}
