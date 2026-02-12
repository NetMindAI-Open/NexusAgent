/**
 * Inbox Panel - Messages from agents (User Inbox) and to agents (Agent Inbox)
 * Uses preloaded data from preloadStore for instant tab switching
 */

import { useState } from 'react';
import { Mail, MailOpen, RefreshCw, CheckCheck, User, Bot } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Markdown } from '@/components/ui';
import { useConfigStore, usePreloadStore } from '@/stores';
import { api } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';

type InboxTab = 'user' | 'agent';

export function InboxPanel() {
  const [activeTab, setActiveTab] = useState<InboxTab>('user');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { userId, agentId } = useConfigStore();
  const {
    // User Inbox
    inbox: userMessages,
    inboxUnreadCount: userUnreadCount,
    inboxLoading: userLoading,
    refreshInbox,
    updateInboxMessage,
    markAllInboxRead,
    // Agent Inbox
    agentInbox: agentMessages,
    agentInboxUnrespondedCount: agentUnrespondedCount,
    agentInboxLoading: agentLoading,
    refreshAgentInbox,
    // updateAgentInboxMessage, // TODO: Future use for marking Agent messages as responded
  } = usePreloadStore();

  const handleRefresh = () => {
    if (activeTab === 'user') {
      refreshInbox(userId);
    } else {
      refreshAgentInbox(agentId);
    }
  };

  const markAsRead = async (messageId: string) => {
    try {
      await api.markMessageRead(messageId);
      updateInboxMessage(messageId, { is_read: true });
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await api.markAllRead(userId);
      markAllInboxRead();
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const toggleExpand = (messageId: string) => {
    if (expandedId === messageId) {
      setExpandedId(null);
    } else {
      setExpandedId(messageId);
      // Mark as read when expanded (only for user inbox)
      if (activeTab === 'user') {
        const msg = userMessages.find((m) => m.message_id === messageId);
        if (msg && !msg.is_read) {
          markAsRead(messageId);
        }
      }
    }
  };

  const loading = activeTab === 'user' ? userLoading : agentLoading;

  // Get source type label for agent inbox
  const getSourceTypeLabel = (sourceType: string) => {
    switch (sourceType) {
      case 'user':
        return 'User';
      case 'agent':
        return 'Agent';
      case 'system':
        return 'System';
      default:
        return sourceType;
    }
  };

  // Get source type color
  const getSourceTypeVariant = (sourceType: string): 'default' | 'accent' | 'success' => {
    switch (sourceType) {
      case 'user':
        return 'accent';
      case 'agent':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-[var(--color-accent)]" />
          Inbox
        </CardTitle>
        <div className="flex items-center gap-2">
          {activeTab === 'user' && userUnreadCount > 0 && (
            <Badge variant="accent" pulse>
              {userUnreadCount}
            </Badge>
          )}
          {activeTab === 'agent' && agentUnrespondedCount > 0 && (
            <Badge variant="accent" pulse>
              {agentUnrespondedCount}
            </Badge>
          )}
          {activeTab === 'user' && (
            <Button variant="ghost" size="icon" onClick={handleMarkAllAsRead} title="Mark all read">
              <CheckCheck className="w-4 h-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>

      {/* Tab Switcher */}
      <div className="px-4 pb-2">
        <div className="flex gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg">
          <button
            onClick={() => {
              setActiveTab('user');
              setExpandedId(null);
            }}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
              activeTab === 'user'
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            <User className="w-3 h-3" />
            User Inbox
            {userUnreadCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-[var(--color-accent)] text-white rounded-full">
                {userUnreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => {
              setActiveTab('agent');
              setExpandedId(null);
            }}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
              activeTab === 'agent'
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            <Bot className="w-3 h-3" />
            Agent Inbox
            {agentUnrespondedCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-[var(--color-accent)] text-white rounded-full">
                {agentUnrespondedCount}
              </span>
            )}
          </button>
        </div>
      </div>

      <CardContent className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {/* User Inbox */}
        {activeTab === 'user' && (
          <>
            {userMessages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-[var(--text-tertiary)] text-sm">No messages</p>
              </div>
            ) : (
              userMessages.map((message) => (
                <button
                  key={message.message_id}
                  onClick={() => toggleExpand(message.message_id)}
                  className={cn(
                    'w-full text-left p-3 rounded-lg transition-all',
                    'border border-[var(--border-default)]',
                    'hover:border-[var(--color-accent)]/50',
                    !message.is_read && 'bg-[var(--accent-10)] border-[var(--color-accent)]/30',
                    expandedId === message.message_id && 'ring-1 ring-[var(--color-accent)]'
                  )}
                >
                  <div className="flex items-start gap-2">
                    {message.is_read ? (
                      <MailOpen className="w-4 h-4 text-[var(--text-tertiary)] mt-0.5" />
                    ) : (
                      <Mail className="w-4 h-4 text-[var(--color-accent)] mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={cn(
                            'text-sm font-medium truncate',
                            !message.is_read ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                          )}
                        >
                          {message.title || 'No title'}
                        </span>
                        <div className="flex items-center gap-1 shrink-0">
                          {message.message_type && (
                            <Badge size="sm" variant="default">
                              {message.message_type}
                            </Badge>
                          )}
                          <span className="text-[10px] text-[var(--text-tertiary)] font-mono">
                            {message.created_at && formatRelativeTime(message.created_at)}
                          </span>
                        </div>
                      </div>
                      <div
                        className={cn(
                          'text-xs mt-1',
                          expandedId === message.message_id
                            ? 'text-[var(--text-secondary)] max-h-[400px] overflow-y-auto'
                            : 'text-[var(--text-tertiary)] line-clamp-2'
                        )}
                      >
                        {expandedId === message.message_id ? (
                          <Markdown content={message.content} />
                        ) : (
                          <span className="whitespace-pre-wrap">{message.content}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </>
        )}

        {/* Agent Inbox */}
        {activeTab === 'agent' && (
          <>
            {agentMessages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-[var(--text-tertiary)] text-sm">No messages</p>
              </div>
            ) : (
              agentMessages.map((message) => (
                <button
                  key={message.message_id}
                  onClick={() => toggleExpand(message.message_id)}
                  className={cn(
                    'w-full text-left p-3 rounded-lg transition-all',
                    'border border-[var(--border-default)]',
                    'hover:border-[var(--color-accent)]/50',
                    !message.if_response && 'bg-[var(--accent-10)] border-[var(--color-accent)]/30',
                    expandedId === message.message_id && 'ring-1 ring-[var(--color-accent)]'
                  )}
                >
                  <div className="flex items-start gap-2">
                    {message.if_response ? (
                      <MailOpen className="w-4 h-4 text-[var(--text-tertiary)] mt-0.5" />
                    ) : (
                      <Mail className="w-4 h-4 text-[var(--color-accent)] mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <Badge size="sm" variant={getSourceTypeVariant(message.source_type)}>
                            {getSourceTypeLabel(message.source_type)}
                          </Badge>
                          <span
                            className={cn(
                              'text-xs truncate',
                              !message.if_response ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                            )}
                          >
                            {message.source_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {!message.if_response && (
                            <Badge size="sm" variant="accent">
                              New
                            </Badge>
                          )}
                          <span className="text-[10px] text-[var(--text-tertiary)] font-mono">
                            {message.created_at && formatRelativeTime(message.created_at)}
                          </span>
                        </div>
                      </div>
                      <div
                        className={cn(
                          'text-xs mt-1',
                          expandedId === message.message_id
                            ? 'text-[var(--text-secondary)] max-h-[400px] overflow-y-auto'
                            : 'text-[var(--text-tertiary)] line-clamp-2'
                        )}
                      >
                        {expandedId === message.message_id ? (
                          <Markdown content={message.content} />
                        ) : (
                          <span className="whitespace-pre-wrap">{message.content}</span>
                        )}
                      </div>
                      {/* Show linked narrative/event if available */}
                      {expandedId === message.message_id && (message.narrative_id || message.event_id) && (
                        <div className="mt-2 pt-2 border-t border-[var(--border-default)] text-[10px] text-[var(--text-tertiary)]">
                          {message.narrative_id && <span className="mr-3">Narrative: {message.narrative_id}</span>}
                          {message.event_id && <span>Event: {message.event_id}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
