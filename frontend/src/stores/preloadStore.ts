/**
 * Preload Store - Cache data on page load for faster tab switching
 *
 * Loads all panel data in parallel when the app initializes:
 * - Inbox messages
 * - Jobs
 * - Agent awareness
 * - Social network list (all contacts)
 * - Chat history (narratives + events)
 * - RAG files
 */

import { create } from 'zustand';
import { api } from '@/lib/api';
import type {
  InboxMessage,
  AgentInboxMessage,
  Job,
  SocialNetworkEntity,
  ChatHistoryEvent,
  ChatHistoryNarrative,
  RAGFileInfo
} from '@/types';

// ────────────────────────────────────────────
// Public interface (fully backward compatible)
// ────────────────────────────────────────────

interface PreloadState {
  // Data
  inbox: InboxMessage[];
  inboxUnreadCount: number;
  agentInbox: AgentInboxMessage[];
  agentInboxUnrespondedCount: number;
  jobs: Job[];
  awareness: string | null;
  awarenessCreateTime: string | null;
  awarenessUpdateTime: string | null;
  socialNetworkList: SocialNetworkEntity[];
  chatHistoryEvents: ChatHistoryEvent[];
  chatHistoryNarratives: ChatHistoryNarrative[];
  ragFiles: RAGFileInfo[];
  ragCompletedCount: number;
  ragPendingCount: number;

  // Loading states
  inboxLoading: boolean;
  agentInboxLoading: boolean;
  jobsLoading: boolean;
  awarenessLoading: boolean;
  socialNetworkLoading: boolean;
  chatHistoryLoading: boolean;
  ragFilesLoading: boolean;

  // Error states
  inboxError: string | null;
  agentInboxError: string | null;
  jobsError: string | null;
  awarenessError: string | null;
  socialNetworkError: string | null;
  chatHistoryError: string | null;
  ragFilesError: string | null;

  // Last loaded params (to detect changes)
  lastUserId: string | null;
  lastAgentId: string | null;

  // Actions
  preloadAll: (agentId: string, userId: string) => Promise<void>;
  refreshInbox: (userId: string) => Promise<void>;
  refreshAgentInbox: (agentId: string) => Promise<void>;
  refreshJobs: (agentId: string, userId?: string, status?: string) => Promise<void>;
  refreshAwareness: (agentId: string) => Promise<void>;
  refreshSocialNetwork: (agentId: string) => Promise<void>;
  refreshChatHistory: (agentId: string, userId: string) => Promise<void>;
  refreshRAGFiles: (agentId: string, userId: string) => Promise<void>;
  addChatHistoryEvent: (event: ChatHistoryEvent) => void;
  updateInboxMessage: (messageId: string, updates: Partial<InboxMessage>) => void;
  updateAgentInboxMessage: (messageId: string, updates: Partial<AgentInboxMessage>) => void;
  markAllInboxRead: () => void;
  clearAll: () => void;
}

// ────────────────────────────────────────────
// Internal helpers: eliminate duplicate code in refresh / preload
// ────────────────────────────────────────────

type SetFn = (partial: Partial<PreloadState>) => void;

/** Generic "load a domain" logic */
async function loadDomain<T>(
  set: SetFn,
  loadingKey: keyof PreloadState,
  errorKey: keyof PreloadState,
  fetcher: () => Promise<T>,
  onSuccess: (data: T) => Partial<PreloadState>,
  fallbackError: string,
) {
  set({ [loadingKey]: true, [errorKey]: null } as Partial<PreloadState>);
  try {
    const result = await fetcher();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((result as any).success) {
      set({ ...onSuccess(result), [loadingKey]: false } as Partial<PreloadState>);
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      set({ [loadingKey]: false, [errorKey]: (result as any).error || fallbackError } as Partial<PreloadState>);
    }
  } catch (error) {
    set({ [loadingKey]: false, [errorKey]: String(error) } as Partial<PreloadState>);
  }
}

/** Extract success data or error info from a single Promise.allSettled result */
function extractSettled<T>(
  result: PromiseSettledResult<T>,
  onFulfilled: (val: T) => Partial<PreloadState>,
  loadingKey: keyof PreloadState,
  errorKey: keyof PreloadState,
  fallbackError: string,
): Partial<PreloadState> {
  if (result.status === 'fulfilled') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((result.value as any).success) {
      return { ...onFulfilled(result.value), [loadingKey]: false };
    }
    return {
      [loadingKey]: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      [errorKey]: (result.value as any).error || fallbackError,
    };
  }
  return { [loadingKey]: false, [errorKey]: String(result.reason) };
}

// ────────────────────────────────────────────
// Store
// ────────────────────────────────────────────

export const usePreloadStore = create<PreloadState>()((set, get) => ({
  // Initial data
  inbox: [],
  inboxUnreadCount: 0,
  agentInbox: [],
  agentInboxUnrespondedCount: 0,
  jobs: [],
  awareness: null,
  awarenessCreateTime: null,
  awarenessUpdateTime: null,
  socialNetworkList: [],
  chatHistoryEvents: [],
  chatHistoryNarratives: [],
  ragFiles: [],
  ragCompletedCount: 0,
  ragPendingCount: 0,

  // Initial loading / error
  inboxLoading: false,
  agentInboxLoading: false,
  jobsLoading: false,
  awarenessLoading: false,
  socialNetworkLoading: false,
  chatHistoryLoading: false,
  ragFilesLoading: false,
  inboxError: null,
  agentInboxError: null,
  jobsError: null,
  awarenessError: null,
  socialNetworkError: null,
  chatHistoryError: null,
  ragFilesError: null,

  lastUserId: null,
  lastAgentId: null,

  // ── Preload all data in parallel ──────────────────

  preloadAll: async (agentId, userId) => {
    const { lastUserId, lastAgentId } = get();
    if (lastUserId === userId && lastAgentId === agentId && get().inbox.length > 0) return;

    set({
      lastUserId: userId,
      lastAgentId: agentId,
      inboxLoading: true, agentInboxLoading: true, jobsLoading: true,
      awarenessLoading: true, socialNetworkLoading: true,
      chatHistoryLoading: true, ragFilesLoading: true,
      inboxError: null, agentInboxError: null, jobsError: null,
      awarenessError: null, socialNetworkError: null,
      chatHistoryError: null, ragFilesError: null,
    });

    const [inbox, agentInbox, jobs, awareness, social, history, rag] = await Promise.allSettled([
      api.getInbox(userId),
      api.getAgentInbox(agentId),
      api.getJobs(agentId),
      api.getAwareness(agentId),
      api.getSocialNetworkList(agentId),
      api.getChatHistory(agentId, userId),
      api.listRAGFiles(agentId, userId),
    ]);

    set({
      ...extractSettled(inbox,
        (r) => ({ inbox: r.messages, inboxUnreadCount: r.unread_count }),
        'inboxLoading', 'inboxError', 'Failed to load inbox'),
      ...extractSettled(agentInbox,
        (r) => ({ agentInbox: r.messages, agentInboxUnrespondedCount: r.unresponded_count }),
        'agentInboxLoading', 'agentInboxError', 'Failed to load agent inbox'),
      ...extractSettled(jobs,
        (r) => ({ jobs: r.jobs }),
        'jobsLoading', 'jobsError', 'Failed to load jobs'),
      ...extractSettled(awareness,
        (r) => ({ awareness: r.awareness || null, awarenessCreateTime: r.create_time || null, awarenessUpdateTime: r.update_time || null }),
        'awarenessLoading', 'awarenessError', 'Failed to load awareness'),
      ...extractSettled(social,
        (r) => ({ socialNetworkList: r.entities || [] }),
        'socialNetworkLoading', 'socialNetworkError', 'No social network data'),
      ...extractSettled(history,
        (r) => ({ chatHistoryEvents: r.events || [], chatHistoryNarratives: r.narratives || [] }),
        'chatHistoryLoading', 'chatHistoryError', 'No chat history'),
      ...extractSettled(rag,
        (r) => ({ ragFiles: r.files || [], ragCompletedCount: r.completed_count || 0, ragPendingCount: r.pending_count || 0 }),
        'ragFilesLoading', 'ragFilesError', 'Failed to load RAG files'),
    } as Partial<PreloadState>);
  },

  // ── Individual refresh methods ────────────────────

  refreshInbox: (userId) => loadDomain(set,
    'inboxLoading', 'inboxError',
    () => api.getInbox(userId),
    (r) => ({ inbox: r.messages, inboxUnreadCount: r.unread_count }),
    'Failed to load inbox'),

  refreshAgentInbox: (agentId) => loadDomain(set,
    'agentInboxLoading', 'agentInboxError',
    () => api.getAgentInbox(agentId),
    (r) => ({ agentInbox: r.messages, agentInboxUnrespondedCount: r.unresponded_count }),
    'Failed to load agent inbox'),

  refreshJobs: (agentId, _userId?, status?) => loadDomain(set,
    'jobsLoading', 'jobsError',
    () => api.getJobs(agentId, undefined, status),
    (r) => ({ jobs: r.jobs }),
    'Failed to load jobs'),

  refreshAwareness: (agentId) => loadDomain(set,
    'awarenessLoading', 'awarenessError',
    () => api.getAwareness(agentId),
    (r) => ({ awareness: r.awareness || null, awarenessCreateTime: r.create_time || null, awarenessUpdateTime: r.update_time || null }),
    'Failed to load awareness'),

  refreshSocialNetwork: (agentId) => loadDomain(set,
    'socialNetworkLoading', 'socialNetworkError',
    () => api.getSocialNetworkList(agentId),
    (r) => ({ socialNetworkList: r.entities || [] }),
    'No social network data'),

  refreshChatHistory: (agentId, userId) => loadDomain(set,
    'chatHistoryLoading', 'chatHistoryError',
    () => api.getChatHistory(agentId, userId),
    (r) => ({ chatHistoryEvents: r.events || [], chatHistoryNarratives: r.narratives || [] }),
    'No chat history'),

  refreshRAGFiles: (agentId, userId) => loadDomain(set,
    'ragFilesLoading', 'ragFilesError',
    () => api.listRAGFiles(agentId, userId),
    (r) => ({ ragFiles: r.files || [], ragCompletedCount: r.completed_count || 0, ragPendingCount: r.pending_count || 0 }),
    'Failed to load RAG files'),

  // ── Mutation helpers ──────────────────────────────

  addChatHistoryEvent: (event) => {
    set((state) => ({
      chatHistoryEvents: [...state.chatHistoryEvents, event].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
    }));
  },

  updateInboxMessage: (messageId, updates) => {
    set((state) => ({
      inbox: state.inbox.map((m) => m.message_id === messageId ? { ...m, ...updates } : m),
      inboxUnreadCount: updates.is_read === true
        ? Math.max(0, state.inboxUnreadCount - 1)
        : state.inboxUnreadCount,
    }));
  },

  updateAgentInboxMessage: (messageId, updates) => {
    set((state) => ({
      agentInbox: state.agentInbox.map((m) => m.message_id === messageId ? { ...m, ...updates } : m),
      agentInboxUnrespondedCount: updates.if_response === true
        ? Math.max(0, state.agentInboxUnrespondedCount - 1)
        : state.agentInboxUnrespondedCount,
    }));
  },

  markAllInboxRead: () => {
    set((state) => ({
      inbox: state.inbox.map((m) => ({ ...m, is_read: true })),
      inboxUnreadCount: 0,
    }));
  },

  clearAll: () => {
    set({
      inbox: [], inboxUnreadCount: 0,
      agentInbox: [], agentInboxUnrespondedCount: 0,
      jobs: [],
      awareness: null, awarenessCreateTime: null, awarenessUpdateTime: null,
      socialNetworkList: [],
      chatHistoryEvents: [], chatHistoryNarratives: [],
      ragFiles: [], ragCompletedCount: 0, ragPendingCount: 0,
      lastUserId: null, lastAgentId: null,
      inboxError: null, agentInboxError: null, jobsError: null,
      awarenessError: null, socialNetworkError: null,
      chatHistoryError: null, ragFilesError: null,
    });
  },
}));
