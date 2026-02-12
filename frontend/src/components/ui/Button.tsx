/**
 * Button component - Bioluminescent Terminal style
 * Button component with glow effects and smooth animations
 */

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'ghost' | 'outline' | 'accent' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  glow?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', glow = false, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          // Base styles
          'relative inline-flex items-center justify-center gap-2',
          'font-medium font-[family-name:var(--font-sans)]',
          'transition-all duration-300 ease-out',
          'disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)]',
          'overflow-hidden',

          // Variants
          variant === 'default' && [
            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
            'border border-[var(--border-default)]',
            'hover:bg-[var(--bg-elevated)] hover:border-[var(--border-strong)]',
            'hover:shadow-[var(--shadow-md)]',
            'active:scale-[0.98]',
          ],
          variant === 'ghost' && [
            'bg-transparent text-[var(--text-secondary)]',
            'hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]',
            'active:bg-[var(--bg-tertiary)]',
          ],
          variant === 'outline' && [
            'bg-transparent text-[var(--text-primary)]',
            'border border-[var(--border-default)]',
            'hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)]',
            'hover:shadow-[0_0_20px_var(--accent-glow)]',
            'active:bg-[var(--accent-glow)]',
          ],
          variant === 'accent' && [
            'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)]',
            'text-[#0a0a12]',
            'border border-transparent',
            'shadow-[0_0_20px_var(--accent-glow)]',
            'hover:shadow-[0_0_30px_var(--accent-glow),0_0_60px_var(--accent-glow)]',
            'hover:brightness-110',
            'active:scale-[0.98]',
          ],
          variant === 'danger' && [
            'bg-[var(--color-error)]/10 text-[var(--color-error)]',
            'border border-[var(--color-error)]/30',
            'hover:bg-[var(--color-error)]/20 hover:border-[var(--color-error)]/50',
            'hover:shadow-[0_0_20px_rgba(255,77,109,0.2)]',
          ],

          // Glow effect
          glow && 'animate-glow-pulse',

          // Sizes
          size === 'sm' && 'h-8 px-3 text-xs rounded-lg',
          size === 'md' && 'h-10 px-4 text-sm rounded-xl',
          size === 'lg' && 'h-12 px-6 text-base rounded-xl',
          size === 'icon' && 'h-10 w-10 rounded-xl',

          className
        )}
        {...props}
      >
        {/* Shine effect on hover */}
        <span className="absolute inset-0 overflow-hidden rounded-inherit pointer-events-none">
          <span className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </span>

        {/* Content */}
        <span className="relative z-10 flex items-center gap-2">
          {children}
        </span>
      </button>
    );
  }
);

Button.displayName = 'Button';
