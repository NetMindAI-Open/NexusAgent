/**
 * @file ServiceCard.tsx
 * @description Service status card — displays individual service runtime status and port info
 */

import React from 'react'

interface ServiceCardProps {
  label: string
  status: 'healthy' | 'unhealthy' | 'unknown' | 'stopped' | 'starting' | 'running' | 'crashed'
  port: number | null
  message?: string
  onRestart?: () => void
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; text: string }> = {
  healthy: { color: 'bg-green-500', bg: 'bg-green-50', text: 'Running' },
  running: { color: 'bg-green-500', bg: 'bg-green-50', text: 'Running' },
  starting: { color: 'bg-yellow-500', bg: 'bg-yellow-50', text: 'Starting' },
  unhealthy: { color: 'bg-red-500', bg: 'bg-red-50', text: 'Unhealthy' },
  crashed: { color: 'bg-red-500', bg: 'bg-red-50', text: 'Crashed' },
  stopped: { color: 'bg-gray-400', bg: 'bg-gray-50', text: 'Stopped' },
  unknown: { color: 'bg-gray-400', bg: 'bg-gray-50', text: 'Unknown' }
}

const ServiceCard: React.FC<ServiceCardProps> = ({
  label,
  status,
  port,
  message,
  onRestart
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.unknown

  return (
    <div
      className={`
        rounded-lg border border-gray-200 p-3 ${config.bg}
        transition-all duration-200 hover:shadow-sm
      `}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${config.color} ${
              status === 'healthy' || status === 'running' ? 'status-pulse' : ''
            }`}
          />
          <span className="text-sm font-medium text-gray-800">{label}</span>
        </div>
        {onRestart && (
          <button
            onClick={onRestart}
            className="titlebar-no-drag text-gray-400 hover:text-blue-500 transition-colors"
            title="Restart"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{config.text}</span>
        {port && (
          <span className="text-xs text-gray-400 font-mono">:{port}</span>
        )}
      </div>

      {message && status !== 'healthy' && status !== 'running' && (
        <p className="text-[10px] text-gray-400 mt-1 truncate" title={message}>
          {message}
        </p>
      )}
    </div>
  )
}

export default ServiceCard
