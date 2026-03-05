/**
 * @file PreflightView.tsx
 * @description Phase 1 UI — displays preflight dependency check results
 *
 * Shows a list of dependencies with status icons, system info summary,
 * an optional EverMemOS install toggle, and action buttons to proceed.
 */

import React from 'react'

interface PreflightViewProps {
  result: PreflightResult
  onProceedToInstall: (missingIds: string[]) => void
  onProceedToLaunch: () => void
  onRecheck: () => void
  checking: boolean
  installEverMemOS: boolean
  onToggleEverMemOS: (v: boolean) => void
  lowMemory: boolean
  dockerMemoryGb: number
}

const StatusIcon: React.FC<{ status: 'ok' | 'missing' | 'warning' }> = ({ status }) => {
  if (status === 'ok') return <span className="text-green-500 text-sm">&#10003;</span>
  if (status === 'warning') return <span className="text-yellow-500 text-sm">&#9888;</span>
  return <span className="text-red-500 text-sm">&#10007;</span>
}

const PreflightView: React.FC<PreflightViewProps> = ({
  result,
  onProceedToInstall,
  onProceedToLaunch,
  onRecheck,
  checking,
  installEverMemOS,
  onToggleEverMemOS,
  lowMemory,
  dockerMemoryGb
}) => {
  const missingItems = result.items.filter((item) => item.status !== 'ok')
  const missingIds = missingItems.map((item) => item.id)

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-gray-700">Environment Check</p>

      {/* Dependency list */}
      <div className="space-y-2">
        {result.items.map((item) => (
          <div
            key={item.id}
            className="flex items-start gap-3 p-2.5 bg-gray-50 rounded-lg"
          >
            <div className="mt-0.5">
              <StatusIcon status={item.status} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">{item.label}</span>
                {item.version && (
                  <span className="text-xs text-gray-400">{item.version}</span>
                )}
              </div>
              {item.hint && (
                <p className="text-xs text-gray-500 mt-0.5">{item.hint}</p>
              )}
              {item.manualUrl && item.status === 'missing' && !item.canAutoInstall && (
                <button
                  onClick={() => window.nexus.openExternal(item.manualUrl!)}
                  className="text-xs text-blue-600 hover:text-blue-800 underline mt-0.5"
                >
                  Download
                </button>
              )}
            </div>
            {item.status === 'ok' && (
              <span className="text-xs text-green-600 font-medium shrink-0">Ready</span>
            )}
            {item.status === 'missing' && item.canAutoInstall && (
              <span className="text-xs text-blue-500 shrink-0">Auto-installable</span>
            )}
          </div>
        ))}
      </div>

      {/* System info summary */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
        <span>{result.systemInfo.platform} / {result.systemInfo.arch}</span>
        <span className={lowMemory ? 'text-red-500' : ''}>
          RAM: {result.systemInfo.totalMemoryGb}GB (Docker: {dockerMemoryGb}GB){lowMemory ? ' — EverMemOS disabled' : ''}
        </span>
        {result.systemInfo.freeDiskGb >= 0 && (
          <span>Free disk: {result.systemInfo.freeDiskGb} GB</span>
        )}
        <span>
          Network: {result.systemInfo.networkOk ? (
            <span className="text-green-500">Online</span>
          ) : (
            <span className="text-red-500">Offline</span>
          )}
        </span>
      </div>

      {/* Optional Components */}
      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-xs font-medium text-gray-500 mb-2">Optional Components</p>
        <label className={`titlebar-no-drag flex items-start gap-2.5 ${lowMemory ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
          <input
            type="checkbox"
            checked={installEverMemOS}
            onChange={(e) => onToggleEverMemOS(e.target.checked)}
            disabled={lowMemory}
            className="accent-blue-500 mt-0.5"
          />
          <div>
            <span className="text-sm font-medium text-gray-700">Install EverMemOS (memory system)</span>
            <p className="text-xs text-gray-400 mt-0.5">Requires 6GB Docker memory</p>
          </div>
        </label>
        {lowMemory && (
          <p className="text-xs text-red-500 mt-2">
            Docker memory too low ({dockerMemoryGb}GB). EverMemOS requires at least 6GB. Increase system memory or Docker allocation to enable.
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mt-4">
        <button
          onClick={onRecheck}
          disabled={checking}
          className="titlebar-no-drag px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-40 transition-colors"
        >
          {checking ? 'Checking...' : 'Re-check'}
        </button>
        {result.allReady ? (
          <button
            onClick={onProceedToLaunch}
            className="titlebar-no-drag flex-1 py-2 text-sm font-medium text-white bg-green-500 rounded-lg hover:bg-green-600 transition-colors"
          >
            {installEverMemOS
              ? 'Install EverMemOS & Start Services'
              : 'Environment Ready — Start Services'}
          </button>
        ) : (
          <button
            onClick={() => onProceedToInstall(missingIds)}
            className="titlebar-no-drag flex-1 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
          >
            Install {missingItems.length} Missing Component{missingItems.length > 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  )
}

export default PreflightView
