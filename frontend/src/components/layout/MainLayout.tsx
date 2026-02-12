/**
 * @file_name: MainLayout.tsx
 * @author: Bin Liang
 * @date: 2025-01-15
 * @description: Main Layout - Bioluminescent Terminal Style
 *
 * Layout structure:
 * ┌──────────┬─────────────────────────────┬──────────────────┐
 * │          │                             │ [Tab] [Tab] [Bell]│
 * │  Agent   │        Chat Area            ├──────────────────┤
 * │  List    │                             │                  │
 * │          │     (Spacious chat area)    │  Context Panel   │
 * │          │                             │  (Tab content)   │
 * └──────────┴─────────────────────────────┴──────────────────┘
 *
 * Right-side tabs: Runtime, Awareness, Agent Inbox, Jobs
 * Top-right bell: User Inbox Popover
 */

import { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { ContextPanelHeader, type ContextTab } from './ContextPanelHeader';
import { ContextPanelContent } from './ContextPanelContent';
import { ChatPanel } from '@/components/chat';
import { useConfigStore, usePreloadStore } from '@/stores';

export function MainLayout() {
  const [contextTab, setContextTab] = useState<ContextTab>('runtime');

  const { agentId, userId } = useConfigStore();
  const { preloadAll } = usePreloadStore();

  // Preload all data when component mounts or when agentId/userId changes
  useEffect(() => {
    if (agentId && userId) {
      preloadAll(agentId, userId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, userId]);

  return (
    <div className="h-screen flex bg-[var(--bg-deep)] relative overflow-hidden">
      {/* Background ambient effects */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(var(--accent-primary) 1px, transparent 1px),
              linear-gradient(90deg, var(--accent-primary) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />

        {/* Corner glow effects */}
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-[var(--accent-primary)] rounded-full opacity-[0.03] blur-[100px]" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-[var(--accent-secondary)] rounded-full opacity-[0.03] blur-[100px]" />

        {/* Floating particles */}
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-[var(--accent-primary)] rounded-full opacity-20"
            style={{
              left: `${10 + i * 12}%`,
              top: `${20 + (i % 3) * 25}%`,
              animation: `particle-float ${4 + i * 0.5}s ease-in-out infinite`,
              animationDelay: `${i * 0.3}s`,
            }}
          />
        ))}
      </div>

      {/* Sidebar - Agent List */}
      <Sidebar />

      {/* Main content - 2 columns */}
      <main className="flex-1 flex min-w-0 p-4 gap-4 overflow-hidden relative z-10">
        {/* Chat Panel - Main area, takes up more space */}
        <div className="flex-[3] min-w-[400px] animate-fade-in">
          <ChatPanel />
        </div>

        {/* Context Panel - Right side panel */}
        <div className="flex-[2] min-w-[320px] flex flex-col animate-slide-in-right" style={{ animationDelay: '0.1s' }}>
          {/* Tab Header + User Inbox Bell */}
          <ContextPanelHeader
            activeTab={contextTab}
            onTabChange={setContextTab}
          />

          {/* Tab Content */}
          <ContextPanelContent activeTab={contextTab} />
        </div>
      </main>
    </div>
  );
}

export default MainLayout;
