/**
 * @file_name: AgentInboxPanel.tsx
 * @author: Bin Liang
 * @date: 2025-01-15
 * @description: Agent Inbox Panel - Displays messages sent to the Agent
 * Bioluminescent Terminal style - Deep ocean aesthetics
 * Enhanced with Control Center Dashboard design
 *
 * Used for the Tab content area in the right panel
 */

import { useState, useMemo } from 'react';
import { Mail, MailOpen, RefreshCw, Inbox, User, Cpu, Settings, ChevronRight, Sparkles, TrendingUp } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Markdown } from '@/components/ui';
import { useConfigStore, usePreloadStore } from '@/stores';
import { cn, formatRelativeTime } from '@/lib/utils';

// KPI Card Component
function KPICard({
  label,
  value,
  icon: Icon,
  color = 'accent',
  subtext,
  pulse,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color?: 'accent' | 'success' | 'warning' | 'secondary';
  subtext?: string;
  pulse?: boolean;
}) {
  const colorMap = {
    accent: {
      bg: 'bg-[var(--accent-glow)]',
      icon: 'text-[var(--accent-primary)]',
      value: 'text-[var(--accent-primary)]',
      glow: 'shadow-[0_0_15px_var(--accent-glow)]',
    },
    success: {
      bg: 'bg-[var(--color-success)]/10',
      icon: 'text-[var(--color-success)]',
      value: 'text-[var(--color-success)]',
      glow: 'shadow-[0_0_15px_rgba(34,197,94,0.2)]',
    },
    warning: {
      bg: 'bg-[var(--color-warning)]/10',
      icon: 'text-[var(--color-warning)]',
      value: 'text-[var(--color-warning)]',
      glow: 'shadow-[0_0_15px_rgba(234,179,8,0.2)]',
    },
    secondary: {
      bg: 'bg-[var(--accent-secondary)]/10',
      icon: 'text-[var(--accent-secondary)]',
      value: 'text-[var(--accent-secondary)]',
      glow: 'shadow-[0_0_15px_rgba(192,132,252,0.2)]',
    },
  };

  const colors = colorMap[color];

  return (
    <div
      className={cn(
        'p-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)]',
        'transition-all duration-300 hover:border-[var(--accent-primary)]/30',
        pulse && colors.glow
      )}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center', colors.bg)}>
          <Icon className={cn('w-3 h-3', colors.icon, pulse && 'animate-pulse')} />
        </div>
        <span className="text-[9px] text-[var(--text-tertiary)] uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className={cn('text-lg font-bold font-mono', colors.value)}>{value}</div>
      {subtext && <div className="text-[8px] text-[var(--text-tertiary)] mt-0.5 font-mono truncate">{subtext}</div>}
    </div>
  );
}

// Source Distribution Mini Chart
function SourceDistribution({ messages }: { messages: Array<{ source_type: string }> }) {
  const stats = useMemo(() => {
    const counts = {
      user: messages.filter((m) => m.source_type === 'user').length,
      agent: messages.filter((m) => m.source_type === 'agent').length,
      system: messages.filter((m) => m.source_type === 'system').length,
    };
    return counts;
  }, [messages]);

  const total = messages.length || 1;

  if (messages.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[9px] font-mono text-[var(--text-tertiary)]">
        <span>Source Distribution</span>
        <span>{messages.length} total</span>
      </div>
      <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden flex">
        {stats.user > 0 && (
          <div
            className="bg-[var(--accent-primary)] transition-all duration-500"
            style={{ width: `${(stats.user / total) * 100}%` }}
            title={`Users: ${stats.user}`}
          />
        )}
        {stats.agent > 0 && (
          <div
            className="bg-[var(--color-success)] transition-all duration-500"
            style={{ width: `${(stats.agent / total) * 100}%` }}
            title={`Agents: ${stats.agent}`}
          />
        )}
        {stats.system > 0 && (
          <div
            className="bg-[var(--text-tertiary)] transition-all duration-500"
            style={{ width: `${(stats.system / total) * 100}%` }}
            title={`System: ${stats.system}`}
          />
        )}
      </div>
      <div className="flex flex-wrap gap-2 text-[8px] font-mono">
        {stats.user > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)]" />
            <span className="text-[var(--text-tertiary)]">{stats.user} from users</span>
          </span>
        )}
        {stats.agent > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
            <span className="text-[var(--text-tertiary)]">{stats.agent} from agents</span>
          </span>
        )}
        {stats.system > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--text-tertiary)]" />
            <span className="text-[var(--text-tertiary)]">{stats.system} from system</span>
          </span>
        )}
      </div>
    </div>
  );
}

export function AgentInboxPanel() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { agentId } = useConfigStore();
  const {
    agentInbox: messages,
    agentInboxUnrespondedCount: unrespondedCount,
    agentInboxLoading: loading,
    refreshAgentInbox,
  } = usePreloadStore();

  const handleRefresh = () => {
    refreshAgentInbox(agentId);
  };

  const toggleExpand = (messageId: string) => {
    setExpandedId(expandedId === messageId ? null : messageId);
  };

  // Calculate inbox metrics
  const inboxMetrics = useMemo(() => {
    const responded = messages.filter((m) => m.if_response).length;
    const responseRate = messages.length > 0 ? Math.round((responded / messages.length) * 100) : 0;
    const userMessages = messages.filter((m) => m.source_type === 'user').length;
    return { responded, responseRate, userMessages };
  }, [messages]);

  // Get source type configuration
  const getSourceTypeConfig = (sourceType: string) => {
    switch (sourceType) {
      case 'user':
        return {
          label: 'User',
          variant: 'accent' as const,
          icon: User,
          bgClass: 'bg-[var(--accent-glow)]',
          iconColor: 'text-[var(--accent-primary)]'
        };
      case 'agent':
        return {
          label: 'Agent',
          variant: 'success' as const,
          icon: Cpu,
          bgClass: 'bg-[var(--color-success)]/10',
          iconColor: 'text-[var(--color-success)]'
        };
      case 'system':
        return {
          label: 'System',
          variant: 'default' as const,
          icon: Settings,
          bgClass: 'bg-[var(--bg-tertiary)]',
          iconColor: 'text-[var(--text-tertiary)]'
        };
      default:
        return {
          label: sourceType,
          variant: 'default' as const,
          icon: Mail,
          bgClass: 'bg-[var(--bg-tertiary)]',
          iconColor: 'text-[var(--text-tertiary)]'
        };
    }
  };

  return (
    <Card variant="glass" className="flex flex-col h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[var(--accent-primary)]/10 flex items-center justify-center">
            <Inbox className="w-4 h-4 text-[var(--accent-primary)]" />
          </div>
          <span>Agent Inbox</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          {unrespondedCount > 0 && (
            <Badge variant="accent" pulse glow className="font-mono">
              {unrespondedCount}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
            className="hover:bg-[var(--accent-glow)]"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>

      {/* Dashboard KPI Section */}
      {messages.length > 0 && (
        <div className="px-4 pb-3 space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <KPICard
              label="New"
              value={unrespondedCount}
              icon={Sparkles}
              color="accent"
              pulse={unrespondedCount > 0}
              subtext="Unresponded"
            />
            <KPICard
              label="From Users"
              value={inboxMetrics.userMessages}
              icon={User}
              color="secondary"
              subtext="Human sources"
            />
            <KPICard
              label="Response"
              value={`${inboxMetrics.responseRate}%`}
              icon={TrendingUp}
              color="success"
              subtext="Rate"
            />
          </div>
          <SourceDistribution messages={messages} />
        </div>
      )}

      <CardContent className="flex-1 overflow-y-auto space-y-3 min-h-0 py-2">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-8">
              <div className="w-14 h-14 rounded-2xl bg-[var(--accent-primary)]/10 mx-auto mb-4 flex items-center justify-center">
                <Inbox className="w-7 h-7 text-[var(--accent-primary)]" />
              </div>
              <p className="text-[var(--text-secondary)] text-sm font-medium mb-1">No messages</p>
              <p className="text-[var(--text-tertiary)] text-xs">Messages from users and agents will appear here</p>
            </div>
          </div>
        ) : (
          messages.map((message) => {
            const sourceConfig = getSourceTypeConfig(message.source_type);
            const SourceIcon = sourceConfig.icon;
            const isExpanded = expandedId === message.message_id;
            const isNew = !message.if_response;

            return (
              <button
                key={message.message_id}
                onClick={() => toggleExpand(message.message_id)}
                className={cn(
                  'w-full text-left p-4 rounded-xl transition-all duration-300 group',
                  'border bg-[var(--bg-elevated)]',
                  isExpanded
                    ? 'border-[var(--accent-primary)]/30 shadow-[0_0_20px_var(--accent-glow)]'
                    : 'border-[var(--border-subtle)] hover:border-[var(--accent-primary)]/20 hover:shadow-lg',
                  isNew && 'bg-[var(--accent-glow)] border-[var(--accent-primary)]/30'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300',
                    sourceConfig.bgClass,
                    isNew && 'shadow-[0_0_15px_var(--accent-glow)]'
                  )}>
                    {isNew ? (
                      <Mail className="w-4 h-4 text-[var(--accent-primary)]" />
                    ) : (
                      <MailOpen className="w-4 h-4 text-[var(--text-tertiary)]" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <Badge size="sm" variant={sourceConfig.variant} className="shrink-0">
                          <SourceIcon className="w-2.5 h-2.5 mr-1" />
                          {sourceConfig.label}
                        </Badge>
                        <span
                          className={cn(
                            'text-xs truncate font-mono',
                            isNew ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                          )}
                        >
                          {message.source_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {isNew && (
                          <Badge size="sm" variant="accent" glow>
                            <Sparkles className="w-2.5 h-2.5 mr-1" />
                            New
                          </Badge>
                        )}
                        <span className="text-[9px] text-[var(--text-tertiary)] font-mono">
                          {message.created_at && formatRelativeTime(message.created_at)}
                        </span>
                        <ChevronRight className={cn(
                          'w-3.5 h-3.5 text-[var(--text-tertiary)] transition-transform duration-300',
                          isExpanded && 'rotate-90'
                        )} />
                      </div>
                    </div>
                    <div
                      className={cn(
                        'text-xs mt-2 transition-all duration-300',
                        isExpanded
                          ? 'text-[var(--text-secondary)] max-h-[400px] overflow-y-auto p-3 bg-[var(--bg-sunken)] rounded-lg border border-[var(--border-subtle)]'
                          : 'text-[var(--text-tertiary)] line-clamp-2'
                      )}
                    >
                      {isExpanded ? (
                        <Markdown content={message.content} />
                      ) : (
                        <span className="whitespace-pre-wrap">{message.content}</span>
                      )}
                    </div>
                    {/* Display associated narrative/event */}
                    {isExpanded && (message.narrative_id || message.event_id) && (
                      <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)] font-mono flex items-center gap-4">
                        {message.narrative_id && (
                          <span className="flex items-center gap-1.5">
                            <span className="text-[var(--accent-primary)]">Narrative:</span>
                            {message.narrative_id}
                          </span>
                        )}
                        {message.event_id && (
                          <span className="flex items-center gap-1.5">
                            <span className="text-[var(--accent-secondary)]">Event:</span>
                            {message.event_id}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

export default AgentInboxPanel;
