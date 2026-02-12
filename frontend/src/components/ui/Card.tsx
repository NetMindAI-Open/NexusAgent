/**
 * Card component - Bioluminescent Terminal style
 * Card component with subtle glowing borders and glass texture
 */

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'elevated' | 'sunken';
  glow?: boolean;
  noPadding?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', glow = false, noPadding = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          // Base styles
          'relative rounded-2xl transition-all duration-300',
          'overflow-hidden',

          // Variants
          variant === 'default' && [
            'bg-[var(--gradient-card)]',
            'border border-[var(--border-default)]',
            'shadow-[var(--shadow-sm)]',
          ],
          variant === 'glass' && [
            'bg-[var(--glass-bg)]',
            'backdrop-blur-xl saturate-150',
            'border border-[var(--glass-border)]',
          ],
          variant === 'elevated' && [
            'bg-[var(--bg-elevated)]',
            'border border-[var(--border-default)]',
            'shadow-[var(--shadow-md)]',
          ],
          variant === 'sunken' && [
            'bg-[var(--bg-sunken)]',
            'border border-[var(--border-subtle)]',
            'shadow-[var(--shadow-inset)]',
          ],

          // Glow effect
          glow && [
            'shadow-[var(--shadow-glow)]',
            'border-[var(--accent-primary)]/30',
          ],

          className
        )}
        {...props}
      >
        {/* Top gradient line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)]/20 to-transparent" />

        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card Header - header area
export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'px-5 py-4',
        'border-b border-[var(--border-subtle)]',
        'flex items-center justify-between',
        'bg-[var(--bg-secondary)]/30',
        className
      )}
      {...props}
    />
  )
);
CardHeader.displayName = 'CardHeader';

// Card Content - content area
export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('p-5', className)}
      {...props}
    />
  )
);
CardContent.displayName = 'CardContent';

// Card Title - title text
export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        'text-sm font-semibold',
        'font-[family-name:var(--font-display)]',
        'text-[var(--text-primary)]',
        'tracking-tight',
        className
      )}
      {...props}
    />
  )
);
CardTitle.displayName = 'CardTitle';

// Card Footer - footer area
export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'px-5 py-4',
        'border-t border-[var(--border-subtle)]',
        'bg-[var(--bg-secondary)]/20',
        className
      )}
      {...props}
    />
  )
);
CardFooter.displayName = 'CardFooter';
