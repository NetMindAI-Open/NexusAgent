/**
 * @file GuidedInstallView.tsx
 * @description Phase 2 UI — guided dependency installation with per-item retry/skip
 *
 * Each dependency shows its status, real-time output, and action buttons.
 * Failed items provide manual download links.
 */

import React, { useEffect, useState } from 'react'

interface GuidedInstallViewProps {
  missingIds: string[]
  onComplete: () => void
  onBack: () => void
}

const StatusIcon: React.FC<{ status: InstallerStatus }> = ({ status }) => {
  switch (status) {
    case 'done': return <span className="text-green-500 text-sm">&#10003;</span>
    case 'running': return (
      <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    )
    case 'error': return <span className="text-red-500 text-sm">&#10007;</span>
    case 'skipped': return <span className="text-gray-400 text-sm">&#8212;</span>
    default: return <span className="text-gray-300 text-sm">&#9679;</span>
  }
}

const GuidedInstallView: React.FC<GuidedInstallViewProps> = ({
  missingIds,
  onComplete,
  onBack
}) => {
  const [states, setStates] = useState<Map<string, InstallerState>>(new Map())
  const [installing, setInstalling] = useState(false)
  const [done, setDone] = useState(false)

  // Listen for installer updates
  useEffect(() => {
    const unsub = window.nexus.onInstallerUpdate((state: InstallerState) => {
      setStates((prev) => {
        const next = new Map(prev)
        next.set(state.id, state)
        return next
      })
    })
    return unsub
  }, [])

  // Check if all done
  useEffect(() => {
    if (states.size === 0) return
    const allFinished = missingIds.every((id) => {
      const s = states.get(id)
      return s && (s.status === 'done' || s.status === 'skipped')
    })
    if (allFinished && installing) {
      setDone(true)
      setInstalling(false)
    }
  }, [states, missingIds, installing])

  // Auto-proceed when done
  useEffect(() => {
    if (done) {
      const timer = setTimeout(onComplete, 1000)
      return () => clearTimeout(timer)
    }
  }, [done, onComplete])

  const handleInstallAll = async () => {
    setInstalling(true)
    setDone(false)
    await window.nexus.installAllDeps(missingIds)
  }

  const handleRetry = async (id: string) => {
    await window.nexus.retryDep(id)
  }

  const handleSkip = (id: string) => {
    window.nexus.skipDep(id)
  }

  const doneCount = missingIds.filter((id) => {
    const s = states.get(id)
    return s && (s.status === 'done' || s.status === 'skipped')
  }).length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-700">Install Dependencies</p>
        <span className="text-xs text-gray-400">{doneCount}/{missingIds.length} completed</span>
      </div>

      {/* Installer list */}
      <div className="space-y-2">
        {missingIds.map((id) => {
          const state = states.get(id)
          const status = state?.status ?? 'pending'
          const label = state?.label ?? id

          return (
            <div key={id} className="p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <StatusIcon status={status} />
                <span className={`text-sm flex-1 ${
                  status === 'running' ? 'text-blue-600 font-medium' :
                  status === 'error' ? 'text-red-600' :
                  status === 'done' ? 'text-gray-600' :
                  'text-gray-500'
                }`}>
                  {label}
                </span>

                {/* Action buttons */}
                {status === 'error' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRetry(id)}
                      className="titlebar-no-drag px-2.5 py-1 text-xs text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
                    >
                      Retry
                    </button>
                    {state?.canSkip && (
                      <button
                        onClick={() => handleSkip(id)}
                        className="titlebar-no-drag px-2.5 py-1 text-xs text-gray-500 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                      >
                        Skip
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Real-time output */}
              {status === 'running' && state?.currentOutput && (
                <p className="text-xs text-gray-400 mt-1.5 truncate pl-6">{state.currentOutput}</p>
              )}

              {/* Error message */}
              {status === 'error' && state?.error && (
                <p className="text-xs text-red-500 mt-1.5 pl-6 break-words">{state.error}</p>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom actions */}
      <div className="flex gap-3">
        <button
          onClick={onBack}
          disabled={installing}
          className="titlebar-no-drag px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-40 transition-colors"
        >
          Back
        </button>
        {done ? (
          <button
            onClick={onComplete}
            className="titlebar-no-drag flex-1 py-2 text-sm font-medium text-white bg-green-500 rounded-lg hover:bg-green-600 transition-colors"
          >
            All Done — Start Services
          </button>
        ) : (
          <button
            onClick={handleInstallAll}
            disabled={installing}
            className="titlebar-no-drag flex-1 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-40 transition-colors"
          >
            {installing ? 'Installing...' : 'Install All'}
          </button>
        )}
      </div>
    </div>
  )
}

export default GuidedInstallView
