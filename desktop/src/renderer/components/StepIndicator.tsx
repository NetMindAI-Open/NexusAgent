/**
 * @file StepIndicator.tsx
 * @description Setup Wizard step indicator
 */

import React from 'react'

interface Step {
  label: string
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep: number
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, currentStep }) => {
  return (
    <div className="flex items-center justify-center gap-1 py-4">
      {steps.map((step, index) => {
        const isActive = index === currentStep
        const isCompleted = index < currentStep

        return (
          <React.Fragment key={index}>
            {/* Step dot */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`
                  w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium
                  transition-all duration-300
                  ${isCompleted
                    ? 'bg-blue-500 text-white'
                    : isActive
                      ? 'bg-blue-500 text-white ring-4 ring-blue-100'
                      : 'bg-gray-200 text-gray-500'
                  }
                `}
              >
                {isCompleted ? (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={`text-[10px] whitespace-nowrap ${
                  isActive ? 'text-blue-600 font-medium' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < steps.length - 1 && (
              <div
                className={`
                  w-8 h-0.5 mb-5
                  ${index < currentStep ? 'bg-blue-500' : 'bg-gray-200'}
                `}
              />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

export default StepIndicator
