/**
 * @file_name: ContextPanelHeader.tsx
 * @author: Bin Liang
 * @date: 2025-01-15
 * @description: Context Panel Header - Bioluminescent Terminal style
 *
 * Tab options:
 * - Runtime: Execution steps / Narrative history
 * - Awareness: Self-awareness / Social network
 * - Agent Inbox: Messages received by the agent
 * - Jobs: Task management
 */

import { Play, Brain, Inbox, Calendar, Puzzle } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { UserInboxPopover } from '@/components/inbox';
import { usePreloadStore } from '@/stores';
import { cn } from '@/lib/utils';

export type ContextTab = 'runtime' | 'awareness' | 'inbox' | 'jobs' | 'skills';

interface ContextPanelHeaderProps {
  activeTab: ContextTab;
  onTabChange: (tab: ContextTab) => void;
}

const tabs: { id: ContextTab; icon: typeof Play; label: string }[] = [
  { id: 'runtime', icon: Play, label: 'Runtime' },
  { id: 'awareness', icon: Brain, label: 'Agent Config' },
  { id: 'inbox', icon: Inbox, label: 'Agent Inbox' },
  { id: 'jobs', icon: Calendar, label: 'Jobs' },
  { id: 'skills', icon: Puzzle, label: 'Skills' },
];

export function ContextPanelHeader({ activeTab, onTabChange }: ContextPanelHeaderProps) {
  const { agentInboxUnrespondedCount } = usePreloadStore();

  return (
    <div className="flex items-center justify-between mb-3 px-1">
      {/* Tab Buttons */}
      <TooltipProvider delayDuration={300}>
        <Tabs value={activeTab} onValueChange={(value) => onTabChange(value as ContextTab)}>
          <TabsList className="bg-[var(--bg-secondary)] border border-[var(--border-default)] p-1 rounded-xl">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const hasNotification = tab.id === 'inbox' && agentInboxUnrespondedCount > 0;

              return (
                <Tooltip key={tab.id}>
                  <TooltipTrigger asChild>
                    <TabsTrigger
                      value={tab.id}
                      className={cn(
                        'relative px-3 py-2 rounded-lg transition-all duration-200',
                        'data-[state=active]:bg-[var(--bg-elevated)]',
                        'data-[state=active]:text-[var(--accent-primary)]',
                        'data-[state=active]:shadow-[0_0_15px_var(--accent-glow)]',
                        'data-[state=active]:border-[var(--accent-primary)]/30',
                        'data-[state=inactive]:text-[var(--text-tertiary)]',
                        'data-[state=inactive]:hover:text-[var(--text-secondary)]',
                        'data-[state=inactive]:hover:bg-[var(--bg-tertiary)]'
                      )}
                    >
                      <Icon className="w-4 h-4" />

                      {/* Notification badge */}
                      {hasNotification && (
                        <span className="absolute -top-1 -right-1 h-4 min-w-4 px-1 flex items-center justify-center text-[9px] font-bold bg-[var(--color-error)] text-white rounded-full shadow-[0_0_8px_rgba(255,77,109,0.5)]">
                          {agentInboxUnrespondedCount > 9 ? '9+' : agentInboxUnrespondedCount}
                        </span>
                      )}

                      {/* Active indicator line */}
                      <span className={cn(
                        'absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-[var(--accent-primary)] rounded-full transition-all duration-300',
                        activeTab === tab.id ? 'w-1/2 opacity-100' : 'w-0 opacity-0'
                      )} />
                    </TabsTrigger>
                  </TooltipTrigger>
                  <TooltipContent
                    className="bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-primary)] shadow-lg"
                  >
                    <p className="text-xs font-medium">{tab.label}</p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </TabsList>
        </Tabs>
      </TooltipProvider>

      {/* User Inbox Notification Bell */}
      <UserInboxPopover />
    </div>
  );
}
