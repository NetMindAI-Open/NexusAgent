/**
 * Sidebar - Bioluminescent Terminal style
 * Agent selection and navigation with dramatic visual effects
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  User,
  LogOut,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  RefreshCw,
  Circle,
  Plus,
  Pencil,
  Check,
  X,
  Globe,
  Lock,
} from 'lucide-react';
import { Button, ThemeToggle } from '@/components/ui';
import { useConfigStore, useChatStore } from '@/stores';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [deletingAgentId, setDeletingAgentId] = useState<string | null>(null);
  const navigate = useNavigate();

  const { userId, agentId, agents, setAgentId, setAgents, logout } = useConfigStore();
  const { clearAll, clearCurrent } = useChatStore();

  // Fetch agents on mount
  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    setLoadingAgents(true);
    try {
      const res = await api.getAgents(userId);
      if (res.success) {
        setAgents(res.agents);
        // If no agent selected and we have agents, select the first one
        if (!agentId && res.agents.length > 0) {
          setAgentId(res.agents[0].agent_id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleSelectAgent = (id: string) => {
    if (id !== agentId) {
      setAgentId(id);
      clearCurrent(); // Clear current conversation when switching agents
    }
  };

  const handleLogout = () => {
    if (confirm('Are you sure you want to logout?')) {
      logout();
      clearAll();
      navigate('/login');
    }
  };

  const handleClearHistory = async () => {
    if (!confirm('Clear all conversation history?')) return;

    // Call API to delete from database
    if (agentId) {
      try {
        const result = await api.clearHistory(agentId, userId);
        if (result.success) {
          console.log(
            `Cleared history: ${result.narratives_count} narratives, ${result.events_count} events deleted`
          );
        } else {
          console.error('Failed to clear history:', result.error);
        }
      } catch (err) {
        console.error('Error clearing history from database:', err);
      }
    }

    // Clear local state
    clearAll();
  };

  const handleCreateAgent = async () => {
    setCreatingAgent(true);
    try {
      const res = await api.createAgent(userId);
      if (res.success && res.agent) {
        // Add new agent to the list
        const newAgent = {
          agent_id: res.agent.agent_id,
          name: res.agent.name,
          description: res.agent.description,
          status: res.agent.status,
          created_at: res.agent.created_at,
          created_by: userId,
        };
        setAgents([newAgent, ...agents]);
        // Auto-select the new agent
        setAgentId(res.agent.agent_id);
        clearCurrent();
      } else {
        console.error('Failed to create agent:', res.error);
      }
    } catch (err) {
      console.error('Error creating agent:', err);
    } finally {
      setCreatingAgent(false);
    }
  };

  const handleTogglePublic = async (agent: typeof agents[0], e: React.MouseEvent) => {
    e.stopPropagation();
    const newIsPublic = !agent.is_public;
    try {
      const res = await api.updateAgent(agent.agent_id, undefined, undefined, newIsPublic);
      if (res.success) {
        setAgents(agents.map(a =>
          a.agent_id === agent.agent_id ? { ...a, is_public: newIsPublic } : a
        ));
      } else {
        console.error('Failed to toggle public:', res.error);
      }
    } catch (err) {
      console.error('Error toggling public:', err);
    }
  };

  const handleStartEdit = (agent: typeof agents[0], e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingAgentId(agent.agent_id);
    setEditingName(agent.name || agent.agent_id);
  };

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingAgentId(null);
    setEditingName('');
  };

  const handleSaveEdit = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!editingName.trim()) return;

    setSavingName(true);
    try {
      const res = await api.updateAgent(agentId, editingName.trim());
      if (res.success && res.agent) {
        // Update agent in the list
        setAgents(agents.map(a =>
          a.agent_id === agentId
            ? { ...a, name: res.agent?.name }
            : a
        ));
        setEditingAgentId(null);
        setEditingName('');
      } else {
        console.error('Failed to update agent:', res.error);
      }
    } catch (err) {
      console.error('Error updating agent:', err);
    } finally {
      setSavingName(false);
    }
  };

  const handleDeleteAgent = async (agent: typeof agents[0], e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete agent "${agent.name || agent.agent_id}"? This will permanently remove all related data (narratives, events, instances, jobs, etc.).`)) {
      return;
    }

    setDeletingAgentId(agent.agent_id);
    try {
      const res = await api.deleteAgent(agent.agent_id, userId);
      if (res.success) {
        const remaining = agents.filter(a => a.agent_id !== agent.agent_id);
        setAgents(remaining);
        // If the deleted agent is the currently selected one, switch to the next
        if (agentId === agent.agent_id) {
          clearCurrent();
          if (remaining.length > 0) {
            setAgentId(remaining[0].agent_id);
          } else {
            setAgentId('');
          }
        }
      } else {
        console.error('Failed to delete agent:', res.error);
        alert(`Failed to delete agent: ${res.error}`);
      }
    } catch (err) {
      console.error('Error deleting agent:', err);
      alert('Error deleting agent. Please try again.');
    } finally {
      setDeletingAgentId(null);
    }
  };

  return (
    <aside
      className={cn(
        'h-full flex flex-col relative',
        'bg-[var(--bg-secondary)]',
        'border-r border-[var(--border-default)]',
        'transition-all duration-400 ease-out',
        collapsed ? 'w-[72px]' : 'w-72'
      )}
    >
      {/* Gradient edge glow */}
      <div className="absolute top-0 right-0 bottom-0 w-px bg-gradient-to-b from-transparent via-[var(--accent-primary)]/20 to-transparent" />

      {/* Header */}
      <div className="p-4 border-b border-[var(--border-subtle)]">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center gap-3 animate-fade-in">
              {/* Logo icon with glow */}
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center shadow-[0_0_20px_var(--accent-glow)]">
                  <Sparkles className="w-5 h-5 text-[var(--text-inverse)] dark:text-[var(--bg-deep)]" />
                </div>
                <div className="absolute -inset-1 rounded-xl bg-[var(--accent-primary)] opacity-20 blur-md -z-10" />
              </div>
              <div>
                <span className="font-[family-name:var(--font-display)] font-bold text-lg text-[var(--text-primary)] tracking-tight">
                  Nexus<span className="text-[var(--accent-primary)]">Agent</span>
                </span>
                <p className="text-[10px] text-[var(--text-tertiary)] font-mono tracking-wider">INTELLIGENT AGENT PLATFORM</p>
              </div>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className="shrink-0"
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* User Info */}
      {!collapsed && (
        <div className="px-4 py-3 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center border border-[var(--border-default)]">
                <User className="w-5 h-5 text-[var(--text-secondary)]" />
              </div>
              {/* Online indicator */}
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[var(--color-success)] border-2 border-[var(--bg-secondary)]">
                <div className="absolute inset-0 rounded-full bg-[var(--color-success)] animate-ping opacity-50" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[var(--text-primary)] truncate font-[family-name:var(--font-mono)]">
                {userId}
              </p>
              <p className="text-[10px] text-[var(--color-success)] uppercase tracking-wider font-medium">Online</p>
            </div>
          </div>
        </div>
      )}

      {/* Agents List */}
      <div className="flex-1 overflow-y-auto">
        {!collapsed && (
          <div className="p-3">
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                Agents
              </span>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCreateAgent}
                  disabled={creatingAgent}
                  className="w-7 h-7"
                  title="Create New Agent"
                >
                  <Plus className={cn('w-3.5 h-3.5', creatingAgent && 'animate-pulse')} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={fetchAgents}
                  disabled={loadingAgents}
                  className="w-7 h-7"
                  title="Refresh Agents"
                >
                  <RefreshCw className={cn('w-3 h-3', loadingAgents && 'animate-spin')} />
                </Button>
              </div>
            </div>

            {agents.length === 0 ? (
              <div className="text-center py-10 px-4">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[var(--bg-tertiary)] flex items-center justify-center border border-dashed border-[var(--border-default)]">
                  <Bot className="w-8 h-8 text-[var(--text-tertiary)]" />
                </div>
                <p className="text-sm text-[var(--text-tertiary)] mb-4">No agents found</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCreateAgent}
                  disabled={creatingAgent}
                  className="gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Create Agent
                </Button>
              </div>
            ) : (
              <div className="space-y-1.5">
                {agents.map((agent, index) => (
                  <button
                    key={agent.agent_id}
                    onClick={() => handleSelectAgent(agent.agent_id)}
                    className={cn(
                      'w-full text-left p-3 rounded-xl transition-all duration-300',
                      'hover:bg-[var(--bg-tertiary)] group relative',
                      'animate-slide-up',
                      agentId === agent.agent_id && [
                        'bg-[var(--bg-elevated)]',
                        'border border-[var(--accent-primary)]/30',
                        'shadow-[0_0_30px_var(--accent-glow),inset_0_0_20px_var(--accent-glow)]',
                      ],
                      agentId !== agent.agent_id && 'border border-transparent'
                    )}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {/* Active indicator bar */}
                    {agentId === agent.agent_id && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 bg-[var(--accent-primary)] rounded-r-full shadow-[0_0_10px_var(--accent-primary)]" />
                    )}

                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          'w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300',
                          agentId === agent.agent_id
                            ? 'bg-[var(--gradient-primary)] shadow-[0_0_20px_var(--accent-glow)]'
                            : 'bg-[var(--bg-tertiary)] border border-[var(--border-default)] group-hover:border-[var(--accent-primary)]/50 group-hover:shadow-[0_0_15px_var(--accent-glow)]'
                        )}
                      >
                        <Bot className={cn(
                          'w-5 h-5 transition-colors',
                          agentId === agent.agent_id
                            ? 'text-[var(--text-inverse)] dark:text-[var(--bg-deep)]'
                            : 'text-[var(--text-secondary)] group-hover:text-[var(--accent-primary)]'
                        )} />
                      </div>
                      <div className="flex-1 min-w-0 pt-0.5">
                        {editingAgentId === agent.agent_id ? (
                          /* Editing Mode — Input field takes full row */
                          <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <input
                              type="text"
                              value={editingName}
                              onChange={e => setEditingName(e.target.value)}
                              className="flex-1 min-w-0 px-2 py-0.5 text-sm font-mono text-[var(--text-primary)] bg-[var(--bg-tertiary)] border border-[var(--accent-primary)]/50 rounded focus:outline-none focus:border-[var(--accent-primary)]"
                              autoFocus
                              onKeyDown={e => {
                                if (e.key === 'Enter') handleSaveEdit(agent.agent_id, e as any);
                                if (e.key === 'Escape') handleCancelEdit(e as any);
                              }}
                            />
                            <button
                              onClick={(e) => handleSaveEdit(agent.agent_id, e)}
                              disabled={savingName}
                              className="p-1 shrink-0 hover:bg-[var(--color-success)]/20 rounded transition-colors"
                              title="Save (Enter)"
                            >
                              <Check className={cn('w-3.5 h-3.5 text-[var(--color-success)]', savingName && 'animate-pulse')} />
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="p-1 shrink-0 hover:bg-[var(--color-error)]/20 rounded transition-colors"
                              title="Cancel (Esc)"
                            >
                              <X className="w-3.5 h-3.5 text-[var(--color-error)]" />
                            </button>
                          </div>
                        ) : (
                          /* Display Mode */
                          <>
                            {/* First row: Name + status indicator */}
                            <div className="flex items-center gap-1.5">
                              <span
                                className={cn(
                                  'font-mono text-sm truncate transition-colors',
                                  agentId === agent.agent_id
                                    ? 'text-[var(--accent-primary)] font-semibold'
                                    : 'text-[var(--text-primary)] group-hover:text-[var(--accent-primary)]'
                                )}
                              >
                                {agent.name || agent.agent_id}
                              </span>
                              {agent.is_public && agent.created_by !== userId && (
                                <span title={`Public · by ${agent.created_by}`}>
                                  <Globe className="w-3 h-3 text-[var(--text-tertiary)] shrink-0" />
                                </span>
                              )}
                              {agentId === agent.agent_id && (
                                <Circle className="w-2 h-2 shrink-0 fill-[var(--color-success)] text-[var(--color-success)] animate-pulse" />
                              )}
                            </div>
                            {/* Second row: Action button toolbar (shown when selected) */}
                            {agentId === agent.agent_id && (
                              <div className="flex items-center gap-0.5 mt-1">
                                {/* Creator only: Toggle public/private */}
                                {agent.created_by === userId && (
                                  <button
                                    onClick={(e) => handleTogglePublic(agent, e)}
                                    className="p-1 hover:bg-[var(--bg-tertiary)] rounded transition-all"
                                    title={agent.is_public ? 'Set to Private' : 'Set to Public'}
                                  >
                                    {agent.is_public ? (
                                      <Globe className="w-3 h-3 text-[var(--accent-primary)]" />
                                    ) : (
                                      <Lock className="w-3 h-3 text-[var(--text-tertiary)] hover:text-[var(--accent-primary)]" />
                                    )}
                                  </button>
                                )}
                                {/* Everyone: Edit name */}
                                <button
                                  onClick={(e) => handleStartEdit(agent, e)}
                                  className="p-1 hover:bg-[var(--bg-tertiary)] rounded transition-all"
                                  title="Edit name"
                                >
                                  <Pencil className="w-3 h-3 text-[var(--text-tertiary)] hover:text-[var(--accent-primary)]" />
                                </button>
                                {/* Creator only: Delete */}
                                {agent.created_by === userId && (
                                  <button
                                    onClick={(e) => handleDeleteAgent(agent, e)}
                                    disabled={deletingAgentId === agent.agent_id}
                                    className="p-1 hover:bg-[var(--color-error)]/10 rounded transition-all"
                                    title="Delete agent"
                                  >
                                    <Trash2 className={cn(
                                      'w-3 h-3 text-[var(--text-tertiary)] hover:text-[var(--color-error)]',
                                      deletingAgentId === agent.agent_id && 'animate-pulse'
                                    )} />
                                  </button>
                                )}
                              </div>
                            )}
                          </>
                        )}
                        {agent.description && editingAgentId !== agent.agent_id && (
                          <p className="text-xs text-[var(--text-tertiary)] mt-1 line-clamp-2 leading-relaxed">
                            {agent.description}
                          </p>
                        )}
                        {agent.name && agent.name !== agent.agent_id && editingAgentId !== agent.agent_id && (
                          <p className="text-[10px] text-[var(--text-tertiary)] mt-0.5 font-mono opacity-60">
                            {agent.agent_id}
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {collapsed && (
          <div className="p-2 space-y-2">
            {/* Create Agent button in collapsed mode */}
            <button
              onClick={handleCreateAgent}
              disabled={creatingAgent}
              className={cn(
                'w-full aspect-square rounded-xl flex items-center justify-center transition-all',
                'bg-[var(--bg-tertiary)] text-[var(--accent-primary)]',
                'hover:bg-[var(--accent-glow)] hover:shadow-[0_0_20px_var(--accent-glow)]',
                'border border-dashed border-[var(--accent-primary)]/30',
                creatingAgent && 'opacity-50 cursor-not-allowed'
              )}
              title="Create New Agent"
            >
              <Plus className={cn('w-5 h-5', creatingAgent && 'animate-pulse')} />
            </button>
            {agents.slice(0, 4).map((agent, index) => (
              <button
                key={agent.agent_id}
                onClick={() => handleSelectAgent(agent.agent_id)}
                className={cn(
                  'w-full aspect-square rounded-xl flex items-center justify-center transition-all duration-300',
                  'animate-fade-in',
                  agentId === agent.agent_id
                    ? 'bg-[var(--gradient-primary)] shadow-[0_0_20px_var(--accent-glow)]'
                    : 'bg-[var(--bg-tertiary)] border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--accent-primary)]/50 hover:shadow-[0_0_15px_var(--accent-glow)]'
                )}
                style={{ animationDelay: `${index * 50}ms` }}
                title={agent.agent_id}
              >
                <Bot className={cn(
                  'w-5 h-5',
                  agentId === agent.agent_id && 'text-[var(--text-inverse)] dark:text-[var(--bg-deep)]'
                )} />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t border-[var(--border-subtle)] space-y-2">
        {!collapsed ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearHistory}
              className="w-full justify-start gap-2 text-[var(--text-secondary)] hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
            >
              <Trash2 className="w-4 h-4" />
              Clear History
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start gap-2 text-[var(--text-secondary)] hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
            <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)]">
              <ThemeToggle />
              <span className="text-[9px] text-[var(--text-tertiary)] font-mono tracking-wider">v1.0.0</span>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClearHistory}
              title="Clear History"
              className="hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="Logout"
              className="hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
            >
              <LogOut className="w-4 h-4" />
            </Button>
            <ThemeToggle />
          </div>
        )}
      </div>
    </aside>
  );
}
