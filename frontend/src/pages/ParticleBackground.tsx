/**
 * Animated particle background for login page
 */

import { useMemo } from 'react';

/** Pre-generate random properties for 30 particles to avoid recalculation on each render */
function generateParticles(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    key: i,
    width: 2 + Math.random() * 4,
    color: i % 3 === 0 ? 'var(--accent-primary)' : i % 3 === 1 ? 'var(--accent-secondary)' : 'var(--color-success)',
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    opacity: 0.2 + Math.random() * 0.3,
    duration: 4 + Math.random() * 6,
    delay: Math.random() * 3,
  }));
}

export function ParticleBackground() {
  const particles = useMemo(() => generateParticles(30), []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div
          key={p.key}
          className="absolute rounded-full"
          style={{
            width: `${p.width}px`,
            height: `${p.width}px`,
            background: p.color,
            left: p.left,
            top: p.top,
            opacity: p.opacity,
            animation: `particle-float ${p.duration}s ease-in-out infinite`,
            animationDelay: `${p.delay}s`,
          }}
        />
      ))}
    </div>
  );
}
