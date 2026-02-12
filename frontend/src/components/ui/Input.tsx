/**
 * Input component - Bioluminescent Terminal style
 * Input field with focus glow effect
 */

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error = false, icon, type = 'text', ...props }, ref) => {
    return (
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]">
            {icon}
          </div>
        )}
        <input
          type={type}
          ref={ref}
          className={cn(
            // Base styles
            'w-full',
            'bg-[var(--bg-sunken)]',
            'border border-[var(--border-default)]',
            'rounded-xl',
            'px-4 py-2.5',
            'text-[var(--text-primary)]',
            'placeholder:text-[var(--text-tertiary)]',
            'font-[family-name:var(--font-sans)]',
            'transition-all duration-200',

            // Focus styles
            'focus:outline-none',
            'focus:border-[var(--accent-primary)]',
            'focus:shadow-[0_0_0_3px_var(--accent-glow),0_0_20px_var(--accent-glow)]',
            'focus:bg-[var(--bg-primary)]',

            // Hover styles
            'hover:border-[var(--border-strong)]',

            // Disabled styles
            'disabled:opacity-50',
            'disabled:cursor-not-allowed',
            'disabled:bg-[var(--bg-tertiary)]',

            // Error styles
            error && [
              'border-[var(--color-error)]',
              'focus:border-[var(--color-error)]',
              'focus:shadow-[0_0_0_3px_rgba(255,77,109,0.15),0_0_20px_rgba(255,77,109,0.1)]',
            ],

            // Icon padding
            icon && 'pl-10',

            className
          )}
          {...props}
        />

        {/* Bottom glow line on focus */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-px bg-[var(--accent-primary)] transition-all duration-300 peer-focus:w-4/5 opacity-50" />
      </div>
    );
  }
);

Input.displayName = 'Input';
