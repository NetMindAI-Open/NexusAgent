/**
 * Context Panel - Agent awareness, social network list, and file upload
 * Bioluminescent Terminal style - Deep ocean aesthetics
 * Enhanced with Control Center Dashboard design
 */

import { useState, useMemo } from 'react';
import { RefreshCw, Brain, User, Tag, Clock, Users, ChevronDown, ChevronRight, Mail, Phone, Building, Sparkles, Activity, Edit3, Save, X, MessageSquare, Network, TrendingUp, Briefcase, Search, UserCircle, Star, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Markdown, Textarea, Dialog, DialogContent, DialogFooter, Input } from '@/components/ui';
import { usePreloadStore, useConfigStore } from '@/stores';
import { cn, formatRelativeTime } from '@/lib/utils';
import { api } from '@/lib/api';
import { FileUpload } from './FileUpload';
import { RAGUpload } from './RAGUpload';
import { MCPManager } from './MCPManager';
import type { SocialNetworkEntity } from '@/types';

// KPI Card Component
function KPICard({
  label,
  value,
  icon: Icon,
  color = 'accent',
  subtext,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color?: 'accent' | 'success' | 'warning' | 'secondary';
  subtext?: string;
}) {
  const colorMap = {
    accent: {
      bg: 'bg-[var(--accent-glow)]',
      icon: 'text-[var(--accent-primary)]',
      value: 'text-[var(--accent-primary)]',
    },
    success: {
      bg: 'bg-[var(--color-success)]/10',
      icon: 'text-[var(--color-success)]',
      value: 'text-[var(--color-success)]',
    },
    warning: {
      bg: 'bg-[var(--color-warning)]/10',
      icon: 'text-[var(--color-warning)]',
      value: 'text-[var(--color-warning)]',
    },
    secondary: {
      bg: 'bg-[var(--accent-secondary)]/10',
      icon: 'text-[var(--accent-secondary)]',
      value: 'text-[var(--accent-secondary)]',
    },
  };

  const colors = colorMap[color];

  return (
    <div className="p-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] transition-all duration-300 hover:border-[var(--accent-primary)]/30">
      <div className="flex items-center gap-2 mb-1.5">
        <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center', colors.bg)}>
          <Icon className={cn('w-3 h-3', colors.icon)} />
        </div>
        <span className="text-[9px] text-[var(--text-tertiary)] uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className={cn('text-lg font-bold font-mono', colors.value)}>{value}</div>
      {subtext && <div className="text-[8px] text-[var(--text-tertiary)] mt-0.5 font-mono truncate">{subtext}</div>}
    </div>
  );
}

interface EntityCardProps {
  entity: SocialNetworkEntity;
  isCurrentUser: boolean;
  actualChatCount: number;
}

function EntityCard({ entity, isCurrentUser, actualChatCount }: EntityCardProps) {
  const [isExpanded, setIsExpanded] = useState(isCurrentUser);

  // Calculate strength level for visual indicator
  const strengthLevel = entity.relationship_strength >= 0.7 ? 'high' : entity.relationship_strength >= 0.4 ? 'medium' : 'low';

  return (
    <div
      className={cn(
        'rounded-xl border overflow-hidden transition-all duration-300',
        isCurrentUser
          ? 'border-[var(--accent-primary)]/30 bg-[var(--accent-glow)] shadow-[0_0_20px_var(--accent-glow)]'
          : isExpanded
            ? 'border-[var(--border-default)] bg-[var(--bg-elevated)] shadow-lg'
            : 'border-[var(--border-subtle)] bg-[var(--bg-sunken)] hover:border-[var(--border-default)] hover:bg-[var(--bg-elevated)]'
      )}
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center gap-3 text-left transition-all duration-300 group"
      >
        <span className={cn(
          'transition-all duration-300',
          isExpanded ? 'text-[var(--accent-primary)]' : 'text-[var(--text-tertiary)]'
        )}>
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />}
        </span>

        <div className={cn(
          'w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300',
          isCurrentUser
            ? 'bg-[var(--accent-primary)] shadow-[0_0_15px_var(--accent-primary)]'
            : 'bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] group-hover:border-[var(--accent-primary)]/30'
        )}>
          <User className={cn(
            'w-4 h-4 transition-colors',
            isCurrentUser ? 'text-[var(--bg-deep)]' : 'text-[var(--text-secondary)]'
          )} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent-primary)] transition-colors">
              {entity.entity_name || entity.entity_id}
            </span>
            {isCurrentUser && (
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-[var(--accent-primary)] text-[var(--bg-deep)] font-medium uppercase tracking-wider">
                You
              </span>
            )}
          </div>
          <div className="text-[10px] text-[var(--text-tertiary)] font-mono truncate mt-0.5 flex items-center gap-2">
            <span>{entity.entity_type}</span>
            <span className="w-1 h-1 rounded-full bg-[var(--text-tertiary)]" />
            <span>{actualChatCount} chats</span>
          </div>
        </div>

        {/* Strength indicator */}
        <div className="flex items-center gap-2">
          {strengthLevel === 'high' && (
            <Badge variant="success" size="sm" glow>Strong</Badge>
          )}
          {strengthLevel === 'medium' && (
            <Badge variant="warning" size="sm">Medium</Badge>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-[var(--border-subtle)] p-3 space-y-3 bg-[var(--bg-sunken)]/50 animate-fade-in">
          {/* Persona - Communication Style */}
          {entity.persona && (
            <div className="p-3 bg-[var(--accent-primary)]/5 rounded-lg border border-[var(--accent-primary)]/20">
              <div className="text-[9px] text-[var(--accent-primary)] font-medium uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <UserCircle className="w-3 h-3" />
                Communication Style
              </div>
              <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
                {entity.persona}
              </div>
            </div>
          )}

          {/* Related Jobs */}
          {entity.related_job_ids && entity.related_job_ids.length > 0 && (
            <div className="p-3 bg-[var(--color-warning)]/5 rounded-lg border border-[var(--color-warning)]/20">
              <div className="text-[9px] text-[var(--color-warning)] font-medium uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <Briefcase className="w-3 h-3" />
                Related Jobs ({entity.related_job_ids.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {entity.related_job_ids.map((jobId, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-1 text-[9px] rounded-lg bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/20 font-mono"
                    title={jobId}
                  >
                    {jobId.length > 12 ? `${jobId.slice(0, 12)}...` : jobId}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Expertise Domains */}
          {entity.expertise_domains && entity.expertise_domains.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {entity.expertise_domains.map((domain, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] rounded-lg bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/20 font-mono"
                >
                  <Star className="w-2.5 h-2.5" />
                  {domain}
                </span>
              ))}
            </div>
          )}

          {/* Description */}
          {entity.entity_description && (
            <div className="text-xs text-[var(--text-secondary)] leading-relaxed p-3 bg-[var(--bg-elevated)] rounded-lg border border-[var(--border-subtle)]">
              <Markdown content={entity.entity_description} />
            </div>
          )}

          {/* Tags */}
          {entity.tags && entity.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {entity.tags.map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] rounded-lg bg-[var(--accent-secondary)]/10 text-[var(--accent-secondary)] border border-[var(--accent-secondary)]/20 font-mono"
                >
                  <Tag className="w-2.5 h-2.5" />
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Identity Info */}
          {entity.identity_info && Object.keys(entity.identity_info).length > 0 && (
            <div className="space-y-2 p-3 bg-[var(--bg-elevated)] rounded-lg border border-[var(--border-subtle)]">
              <div className="text-[9px] text-[var(--accent-primary)] font-medium uppercase tracking-wider flex items-center gap-1.5">
                <Building className="w-3 h-3" />
                Identity
              </div>
              <div className="grid grid-cols-1 gap-1 text-[10px] font-mono">
                {Object.entries(entity.identity_info).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2">
                    <span className="text-[var(--text-tertiary)] capitalize min-w-[60px]">{key}:</span>
                    <span className="text-[var(--text-secondary)] break-all">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Contact Info */}
          {entity.contact_info && Object.keys(entity.contact_info).length > 0 && (
            <div className="space-y-2 p-3 bg-[var(--bg-elevated)] rounded-lg border border-[var(--border-subtle)]">
              <div className="text-[9px] text-[var(--color-success)] font-medium uppercase tracking-wider flex items-center gap-1.5">
                <Mail className="w-3 h-3" />
                Contact
              </div>
              <div className="grid grid-cols-1 gap-1 text-[10px] font-mono">
                {Object.entries(entity.contact_info).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2">
                    {key === 'email' && <Mail className="w-3 h-3 text-[var(--text-tertiary)]" />}
                    {key === 'phone' && <Phone className="w-3 h-3 text-[var(--text-tertiary)]" />}
                    {!['email', 'phone'].includes(key) && <span className="text-[var(--text-tertiary)] capitalize min-w-[60px]">{key}:</span>}
                    <span className="text-[var(--text-secondary)] truncate">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)] text-[9px] font-mono">
            <div className="flex items-center gap-2 text-[var(--text-tertiary)]">
              <Activity className="w-3 h-3 text-[var(--accent-primary)]" />
              <span>Strength:</span>
              <span className={cn(
                'font-medium',
                strengthLevel === 'high' && 'text-[var(--color-success)]',
                strengthLevel === 'medium' && 'text-[var(--color-warning)]',
                strengthLevel === 'low' && 'text-[var(--text-tertiary)]'
              )}>
                {(entity.relationship_strength * 100).toFixed(0)}%
              </span>
            </div>
            {entity.last_interaction_time && (
              <div className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(entity.last_interaction_time)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function AwarenessPanel() {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editedAwareness, setEditedAwareness] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Search-related state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState<'keyword' | 'semantic'>('semantic');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SocialNetworkEntity[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const {
    awareness,
    awarenessUpdateTime,
    socialNetworkList,
    chatHistoryEvents,
    awarenessLoading,
    socialNetworkLoading,
    awarenessError,
    refreshAwareness,
    refreshSocialNetwork,
  } = usePreloadStore();

  const { agentId, userId } = useConfigStore();

  const handleRefresh = async () => {
    await Promise.all([
      refreshAwareness(agentId),
      refreshSocialNetwork(agentId),
    ]);
  };

  const handleOpenEditModal = () => {
    setEditedAwareness(awareness || '');
    setIsEditModalOpen(true);
  };

  const handleSaveAwareness = async () => {
    if (!agentId) return;

    setIsSaving(true);
    console.log('[AwarenessPanel] Saving awareness for agent:', agentId);
    console.log('[AwarenessPanel] New awareness content (first 100 chars):', editedAwareness.slice(0, 100));

    try {
      const response = await api.updateAwareness(agentId, editedAwareness);
      console.log('[AwarenessPanel] Update response:', response);

      if (response.success) {
        console.log('[AwarenessPanel] Update successful, returned awareness:', response.awareness?.slice(0, 100));
        // Refresh awareness data
        await refreshAwareness(agentId);
        console.log('[AwarenessPanel] Refreshed awareness from store:', awareness?.slice(0, 100));
        setIsEditModalOpen(false);
      } else {
        console.error('[AwarenessPanel] Failed to update awareness:', response.error);
      }
    } catch (error) {
      console.error('[AwarenessPanel] Error updating awareness:', error);
    } finally {
      setIsSaving(false);
    }
  };

  // Search handler
  const handleSearch = async () => {
    if (!agentId || !searchQuery.trim()) return;

    setIsSearching(true);
    setHasSearched(true);

    try {
      const response = await api.searchSocialNetwork(agentId, searchQuery.trim(), searchType, 10);
      if (response.success) {
        setSearchResults(response.entities);
      } else {
        console.error('Search failed:', response.error);
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setHasSearched(false);
  };

  // Trigger search on Enter key
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const isLoading = awarenessLoading || socialNetworkLoading;

  // Calculate actual chat count from chatHistoryEvents for each entity (memoized)
  const entityChatCountMap = useMemo(() => {
    const map = new Map<string, number>();
    chatHistoryEvents.forEach((event) => {
      if (event.user_id) {
        map.set(event.user_id, (map.get(event.user_id) || 0) + 1);
      }
    });
    return map;
  }, [chatHistoryEvents]);

  // Sort social network list: current user first, then by actual chat count (memoized)
  const sortedEntities = useMemo(() => {
    return [...socialNetworkList].sort((a, b) => {
      if (a.entity_id === userId) return -1;
      if (b.entity_id === userId) return 1;
      const countA = entityChatCountMap.get(a.entity_id) || 0;
      const countB = entityChatCountMap.get(b.entity_id) || 0;
      return countB - countA;
    });
  }, [socialNetworkList, userId, entityChatCountMap]);

  // Calculate network metrics
  const networkMetrics = useMemo(() => {
    const totalChats = chatHistoryEvents.length;
    const avgStrength = socialNetworkList.length > 0
      ? socialNetworkList.reduce((sum, e) => sum + e.relationship_strength, 0) / socialNetworkList.length
      : 0;
    const strongConnections = socialNetworkList.filter(e => e.relationship_strength >= 0.7).length;
    return { totalChats, avgStrength: Math.round(avgStrength * 100), strongConnections };
  }, [chatHistoryEvents, socialNetworkList]);

  return (
    <>
      <Card variant="glass" className="flex flex-col h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[var(--accent-secondary)]/10 flex items-center justify-center">
              <Brain className="w-4 h-4 text-[var(--accent-secondary)]" />
            </div>
            <span>Context</span>
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={isLoading}
            title="Refresh"
            className="hover:bg-[var(--accent-glow)]"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </Button>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto space-y-4 min-h-0">
          {/* Dashboard KPI Section */}
          <div className="grid grid-cols-3 gap-2">
            <KPICard
              label="Contacts"
              value={socialNetworkList.length}
              icon={Users}
              color="accent"
              subtext="In network"
            />
            <KPICard
              label="Chats"
              value={networkMetrics.totalChats}
              icon={MessageSquare}
              color="secondary"
              subtext="Total interactions"
            />
            <KPICard
              label="Strong"
              value={networkMetrics.strongConnections}
              icon={TrendingUp}
              color="success"
              subtext={`${networkMetrics.avgStrength}% avg`}
            />
          </div>

          {/* Agent Awareness Section */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[10px] text-[var(--accent-secondary)] font-medium uppercase tracking-wider">
                <Sparkles className="w-3 h-3" />
                Agent Awareness
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleOpenEditModal}
                disabled={awarenessLoading}
                className="h-7 px-2 text-[10px] hover:bg-[var(--accent-glow)] hover:text-[var(--accent-primary)]"
              >
                <Edit3 className="w-3 h-3 mr-1" />
                Edit
              </Button>
            </div>

            {awarenessLoading ? (
              <div className="animate-pulse rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4">
                <div className="space-y-2">
                  <div className="h-3 bg-[var(--bg-tertiary)] rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-tertiary)] rounded w-1/2" />
                  <div className="h-3 bg-[var(--bg-tertiary)] rounded w-2/3" />
                </div>
              </div>
            ) : awarenessError ? (
              <div className="text-xs text-[var(--color-error)] p-3 bg-[var(--color-error)]/10 rounded-xl border border-[var(--color-error)]/20">
                {awarenessError}
              </div>
            ) : awareness ? (
              <div className="p-3 bg-[var(--bg-elevated)] rounded-xl border border-[var(--border-subtle)] space-y-2 relative overflow-hidden">
                {/* Subtle glow effect */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--accent-secondary)]/20 to-transparent" />
                <div className="text-xs max-h-[150px] overflow-y-auto text-[var(--text-secondary)] leading-relaxed">
                  <Markdown content={awareness} />
                </div>
                {awarenessUpdateTime && (
                  <div className="text-[9px] text-[var(--text-tertiary)] font-mono flex items-center gap-1.5 pt-2 border-t border-[var(--border-subtle)]">
                    <Clock className="w-3 h-3 text-[var(--accent-secondary)]" />
                    Updated {formatRelativeTime(awarenessUpdateTime)}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-[var(--text-tertiary)] p-6 bg-[var(--bg-sunken)] rounded-xl border border-[var(--border-subtle)] text-center">
                <Brain className="w-6 h-6 mx-auto mb-2 opacity-30" />
                No awareness data
              </div>
            )}
          </section>

          {/* Divider with glow */}
          <div className="relative">
            <div className="border-t border-[var(--border-subtle)]" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-16 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)]/30 to-transparent" />
          </div>

          {/* Social Network Section */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[10px] text-[var(--accent-primary)] font-medium uppercase tracking-wider">
                <Network className="w-3 h-3" />
                Social Network
              </div>
              <Badge variant="default" size="sm" className="font-mono">{socialNetworkList.length}</Badge>
            </div>

            {/* Semantic search box */}
            <div className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-tertiary)]" />
                  <Input
                    type="text"
                    placeholder="Search contacts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleSearchKeyDown}
                    className="pl-9 pr-3 h-9 text-xs bg-[var(--bg-elevated)] border-[var(--border-subtle)] focus:border-[var(--accent-primary)]/50"
                  />
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSearch}
                  disabled={isSearching || !searchQuery.trim()}
                  className="h-9 px-3 hover:bg-[var(--accent-glow)]"
                >
                  {isSearching ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Search className="w-3.5 h-3.5" />
                  )}
                </Button>
              </div>

              {/* Search type toggle */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSearchType('semantic')}
                  className={cn(
                    'px-2 py-1 text-[9px] rounded-lg transition-all duration-200 font-mono',
                    searchType === 'semantic'
                      ? 'bg-[var(--accent-primary)] text-[var(--bg-deep)]'
                      : 'bg-[var(--bg-elevated)] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                  )}
                >
                  Semantic
                </button>
                <button
                  onClick={() => setSearchType('keyword')}
                  className={cn(
                    'px-2 py-1 text-[9px] rounded-lg transition-all duration-200 font-mono',
                    searchType === 'keyword'
                      ? 'bg-[var(--accent-primary)] text-[var(--bg-deep)]'
                      : 'bg-[var(--bg-elevated)] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                  )}
                >
                  Keyword
                </button>
                {hasSearched && (
                  <button
                    onClick={handleClearSearch}
                    className="ml-auto px-2 py-1 text-[9px] rounded-lg bg-[var(--bg-elevated)] text-[var(--text-tertiary)] hover:text-[var(--color-error)] transition-colors font-mono"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Search results */}
            {hasSearched && (
              <div className="space-y-2">
                <div className="text-[9px] text-[var(--text-tertiary)] font-mono">
                  {isSearching ? 'Searching...' : `${searchResults.length} results found`}
                </div>
                {searchResults.length > 0 && (
                  <div className="space-y-2 p-2 bg-[var(--accent-glow)] rounded-xl border border-[var(--accent-primary)]/20">
                    {searchResults.map((entity) => (
                      <EntityCard
                        key={`search-${entity.entity_id}`}
                        entity={entity}
                        isCurrentUser={entity.entity_id === userId}
                        actualChatCount={entityChatCountMap.get(entity.entity_id) || 0}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Original list (hidden during search) */}
            {!hasSearched && (
              socialNetworkLoading ? (
                <div className="space-y-2">
                  {[1, 2].map((i) => (
                    <div key={i} className="animate-pulse rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-[var(--bg-tertiary)]" />
                        <div className="flex-1 space-y-2">
                          <div className="h-3 bg-[var(--bg-tertiary)] rounded w-2/3" />
                          <div className="h-2 bg-[var(--bg-tertiary)] rounded w-1/3" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : sortedEntities.length === 0 ? (
                <div className="text-xs text-[var(--text-tertiary)] p-6 bg-[var(--bg-sunken)] rounded-xl border border-[var(--border-subtle)] text-center">
                  <Users className="w-6 h-6 mx-auto mb-2 opacity-30" />
                  No contacts yet
                </div>
              ) : (
                <div className="space-y-2">
                  {sortedEntities.map((entity) => (
                    <EntityCard
                      key={entity.entity_id}
                      entity={entity}
                      isCurrentUser={entity.entity_id === userId}
                      actualChatCount={entityChatCountMap.get(entity.entity_id) || 0}
                    />
                  ))}
                </div>
              )
            )}
          </section>

          {/* Divider with glow */}
          <div className="relative">
            <div className="border-t border-[var(--border-subtle)]" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-16 h-px bg-gradient-to-r from-transparent via-[var(--color-success)]/30 to-transparent" />
          </div>

          {/* RAG Upload Section */}
          <RAGUpload />

          {/* Divider */}
          <div className="border-t border-[var(--border-subtle)]" />

          {/* File Upload Section */}
          <FileUpload />

          {/* Divider */}
          <div className="border-t border-[var(--border-subtle)]" />

          {/* MCP Manager Section */}
          <MCPManager />
        </CardContent>
      </Card>

      {/* Edit Awareness Modal */}
      <Dialog
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Agent Awareness"
        size="lg"
      >
        <DialogContent>
          <div className="space-y-3">
            <p className="text-xs text-[var(--text-tertiary)]">
              Edit the agent's self-awareness text. This helps the agent understand its current state, goals, and context.
            </p>
            <Textarea
              value={editedAwareness}
              onChange={(e) => setEditedAwareness(e.target.value)}
              placeholder="Enter agent awareness..."
              rows={12}
              className="font-mono text-sm resize-none"
            />
          </div>
        </DialogContent>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setIsEditModalOpen(false)}
            disabled={isSaving}
          >
            <X className="w-4 h-4 mr-2" />
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleSaveAwareness}
            disabled={isSaving}
            className="bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/80"
          >
            {isSaving ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save
              </>
            )}
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}

export default AwarenessPanel;
