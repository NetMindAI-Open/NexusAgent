/**
 * @file AsciiBanner.tsx
 * @description Gradient ASCII Banner component — brand identity extracted from run.sh
 *
 * Supports two sizes:
 * - normal: used by SetupWizard, full size + subtitle
 * - small: used in Dashboard title bar, compact version + subtitle
 */

import React from 'react'

interface AsciiBannerProps {
  size?: 'normal' | 'small'
}

const ASCII_ART = `    ███╗   ██╗ █████╗ ██████╗ ██████╗  █████╗ ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
    ████╗  ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
    ██╔██╗ ██║███████║██████╔╝██████╔╝███████║██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
    ██║╚██╗██║██╔══██║██╔══██╗██╔══██╗██╔══██║██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
    ██║ ╚████║██║  ██║██║  ██║██║  ██║██║  ██║██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
    ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝`

const SUBTITLE = 'Modular Agent Framework with Long-term Memory'

const AsciiBanner: React.FC<AsciiBannerProps> = ({ size = 'normal' }) => {
  const isSmall = size === 'small'

  return (
    <div className="flex flex-col items-center select-none">
      <div
        className={`ascii-banner ${isSmall ? 'text-[5px] leading-[1.15]' : 'text-[8px] leading-[1.15]'}`}
      >
        {ASCII_ART}
      </div>
      <p className={`text-gray-400 ${isSmall ? 'text-[9px] mt-0.5' : 'text-xs mt-1'}`}>
        {SUBTITLE}
      </p>
    </div>
  )
}

export default AsciiBanner
