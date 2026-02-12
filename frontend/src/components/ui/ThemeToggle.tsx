/**
 * Theme toggle component - Bioluminescent Terminal style
 * Animated theme toggle button
 */

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '@/hooks';
import { Button } from './Button';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
  const { theme, toggleTheme, isDark } = useTheme();

  const Icon = theme === 'system' ? Monitor : isDark ? Moon : Sun;
  const label = theme === 'system' ? 'System' : isDark ? 'Dark' : 'Light';

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      title={`Theme: ${label}`}
      className={cn(
        'relative overflow-hidden group',
        'hover:text-[var(--accent-primary)]',
        'hover:bg-[var(--accent-glow)]'
      )}
    >
      {/* Glow ring on hover */}
      <span className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[var(--accent-primary)]/0 via-[var(--accent-primary)]/10 to-[var(--accent-primary)]/0" />

      {/* Icon with rotation animation */}
      <Icon className={cn(
        'h-4 w-4 relative z-10',
        'transition-all duration-300',
        'group-hover:scale-110',
        isDark && 'group-hover:rotate-12',
        !isDark && 'group-hover:-rotate-12'
      )} />
    </Button>
  );
}
