/**
 * Textarea component - Bioluminescent Terminal style
 * Multi-line text input with focus glow effect
 */

import { forwardRef, type TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error = false, ...props }, ref) => {
    return (
      <div className="relative">
        <textarea
          ref={ref}
          className={cn(
            // Base styles
            'w-full',
            'bg-[var(--bg-sunken)]',
            'border border-[var(--border-default)]',
            'rounded-xl',
            'px-4 py-3',
            'text-[var(--text-primary)]',
            'placeholder:text-[var(--text-tertiary)]',
            'font-[family-name:var(--font-sans)]',
            'transition-all duration-200',
            'resize-none',
            'min-h-[100px]',

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

            // Scrollbar styling
            'scrollbar-thin',

            className
          )}
          {...props}
        />

        {/* Corner decoration */}
        <div className="absolute bottom-2 right-2 w-4 h-4 pointer-events-none opacity-30">
          <svg viewBox="0 0 16 16" fill="none" className="w-full h-full text-[var(--text-tertiary)]">
            <path d="M14 2v12H2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
