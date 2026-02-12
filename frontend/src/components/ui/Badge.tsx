/**
 * Badge component - Bioluminescent Terminal style
 * Status badge with glow effects
 */

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'accent' | 'success' | 'warning' | 'error' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
  glow?: boolean;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', pulse = false, glow = false, children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          // Base styles
          'relative inline-flex items-center justify-center',
          'font-medium font-[family-name:var(--font-mono)]',
          'rounded-full',
          'transition-all duration-200',

          // Variants
          variant === 'default' && [
            'bg-[var(--bg-tertiary)]',
            'text-[var(--text-secondary)]',
            'border border-[var(--border-default)]',
          ],
          variant === 'accent' && [
            'bg-[var(--accent-glow)]',
            'text-[var(--accent-primary)]',
            'border border-[var(--accent-primary)]/30',
          ],
          variant === 'success' && [
            'bg-[var(--color-success)]/10',
            'text-[var(--color-success)]',
            'border border-[var(--color-success)]/30',
          ],
          variant === 'warning' && [
            'bg-[var(--color-warning)]/10',
            'text-[var(--color-warning)]',
            'border border-[var(--color-warning)]/30',
          ],
          variant === 'error' && [
            'bg-[var(--color-error)]/10',
            'text-[var(--color-error)]',
            'border border-[var(--color-error)]/30',
          ],
          variant === 'outline' && [
            'bg-transparent',
            'text-[var(--text-secondary)]',
            'border border-[var(--border-default)]',
          ],

          // Sizes
          size === 'sm' && 'h-5 px-2 text-[10px]',
          size === 'md' && 'h-6 px-2.5 text-xs',
          size === 'lg' && 'h-7 px-3 text-sm',

          // Glow effect
          glow && variant === 'accent' && 'shadow-[0_0_12px_var(--accent-glow)]',
          glow && variant === 'success' && 'shadow-[0_0_12px_rgba(0,255,136,0.2)]',
          glow && variant === 'warning' && 'shadow-[0_0_12px_rgba(251,191,36,0.2)]',
          glow && variant === 'error' && 'shadow-[0_0_12px_rgba(255,77,109,0.2)]',

          className
        )}
        {...props}
      >
        {/* Pulse indicator */}
        {pulse && (
          <span className="absolute -left-px flex h-full items-center">
            <span className={cn(
              'h-2 w-2 rounded-full',
              variant === 'accent' && 'bg-[var(--accent-primary)]',
              variant === 'success' && 'bg-[var(--color-success)]',
              variant === 'warning' && 'bg-[var(--color-warning)]',
              variant === 'error' && 'bg-[var(--color-error)]',
              variant === 'default' && 'bg-[var(--text-tertiary)]',
              'animate-pulse'
            )} />
            <span className={cn(
              'absolute h-2 w-2 rounded-full',
              variant === 'accent' && 'bg-[var(--accent-primary)]',
              variant === 'success' && 'bg-[var(--color-success)]',
              variant === 'warning' && 'bg-[var(--color-warning)]',
              variant === 'error' && 'bg-[var(--color-error)]',
              variant === 'default' && 'bg-[var(--text-tertiary)]',
              'animate-ping opacity-75'
            )} />
          </span>
        )}

        <span className={cn(pulse && 'ml-3')}>
          {children}
        </span>
      </span>
    );
  }
);

Badge.displayName = 'Badge';
