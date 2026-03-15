import React from 'react'
import CameraBox from '../components/CameraBox'
import QuestionBox from '../components/QuestionBox'
import RecordControls from '../components/RecordControls'

export default function Interview() {
  return (
    <div className="flex flex-col h-[75vh]">
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-4">
          <CameraBox />
        </div>
        <div className="p-4">
          <QuestionBox />
        </div>
      </div>

      <div className="mt-6 p-4">
        <RecordControls />
      </div>
    </div>
  )
}
