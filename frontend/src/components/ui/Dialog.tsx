/**
 * Dialog Component - Bioluminescent Terminal style
 * Modal dialog with backdrop and animations
 */

import { useEffect, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './Button';

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl';
}

export function Dialog({ isOpen, onClose, title, children, className, size = 'md' }: DialogProps) {
  // Handle escape key
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
    '6xl': 'max-w-6xl',
  };

  // Portal to document.body to avoid fixed positioning offset caused by parent element transform
  return createPortal(
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="fixed inset-0 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div
            className={cn(
              'relative w-full rounded-2xl',
              'bg-[var(--bg-elevated)] border border-[var(--border-default)]',
              'shadow-2xl shadow-black/40',
              'animate-slide-up transition-[max-width] duration-300 ease-out',
              sizeClasses[size],
              className
            )}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Glow effect */}
            <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-[var(--accent-primary)]/20 to-transparent opacity-50 blur-sm pointer-events-none" />

            {/* Content wrapper */}
            <div className="relative">
              {/* Header */}
              {title && (
                <div className="flex items-center justify-between p-4 border-b border-[var(--border-subtle)]">
                  <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onClose}
                    className="w-8 h-8 hover:bg-[var(--bg-tertiary)]"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              )}

              {/* Body */}
              <div className={cn(!title && 'pt-4')}>
                {children}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

// Dialog sub-components for flexibility
export function DialogContent({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('p-4', className)}>
      {children}
    </div>
  );
}

export function DialogFooter({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center justify-end gap-3 p-4 border-t border-[var(--border-subtle)]', className)}>
      {children}
    </div>
  );
}
