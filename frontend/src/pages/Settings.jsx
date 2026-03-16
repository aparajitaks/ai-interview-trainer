import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function SettingRow({ children }) {
  return <div className="rounded-xl p-4 bg-white/6 backdrop-blur-md border border-white/10 shadow-lg">{children}</div>
}

export default function Settings() {
  const navigate = useNavigate()
  const [dark, setDark] = useState(true)

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-black p-8">
      <div className="w-full max-w-3xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-white">Settings</h1>
          <p className="mt-2 text-slate-300">Configure your UI and device preferences (UI only).</p>
        </div>

        <div className="space-y-4">
          <SettingRow>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-white font-semibold">Theme</div>
                <div className="text-sm text-slate-300">Toggle dark / light (UI only)</div>
              </div>
              <div>
                <label className="inline-flex items-center space-x-3">
                  <span className="relative">
                    <input type="checkbox" checked={dark} onChange={() => setDark(!dark)} className="sr-only peer" />
                    <div className="w-11 h-6 bg-white/10 rounded-full shadow-inner peer-checked:bg-indigo-600 transition-colors" />
                    <div className={`absolute left-0 top-0 w-6 h-6 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform`} />
                  </span>
                </label>
              </div>
            </div>
          </SettingRow>

          <SettingRow>
            <div>
              <div className="text-white font-semibold">Camera Settings</div>
              <div className="text-sm text-slate-300 mt-2">Preferred camera and resolution (UI only)</div>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                <select className="p-2 rounded-md bg-white/5 text-white border border-white/8">
                  <option>Default Camera</option>
                  <option>External USB Camera</option>
                </select>
                <select className="p-2 rounded-md bg-white/5 text-white border border-white/8">
                  <option>720p</option>
                  <option>1080p</option>
                </select>
              </div>
            </div>
          </SettingRow>

          <SettingRow>
            <div>
              <div className="text-white font-semibold">Audio Settings</div>
              <div className="text-sm text-slate-300 mt-2">Microphone selection and input level (UI only)</div>
              <div className="mt-3">
                <select className="p-2 rounded-md bg-white/5 text-white border border-white/8">
                  <option>Default Microphone</option>
                  <option>External Microphone</option>
                </select>
                <div className="mt-3">
                  <input type="range" min="0" max="100" defaultValue={75} className="w-full" />
                </div>
              </div>
            </div>
          </SettingRow>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-5 py-3 rounded-lg bg-white/6 backdrop-blur-md border border-white/10 text-white font-medium shadow-md transition-all duration-200 hover:scale-105"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}
