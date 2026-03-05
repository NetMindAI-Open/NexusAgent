/**
 * @file_name: useAutoRefresh.ts
 * @author: Bin Liang
 * @date: 2026-03-04
 * @description: Smart auto-refresh hook for background data polling
 *
 * Features:
 * 1. Tiered polling — high-freq (10s): inbox/agentInbox, mid-freq (30s): jobs/ragFiles/awareness/socialNetwork
 * 2. Visibility API — pauses all polling when the tab is hidden, refreshes immediately on re-focus
 * 3. Exposes refreshAll() for full data reload after agent execution completes
 *
 * Design:
 * - Zero requests while the tab is hidden
 * - Uses setInterval for simplicity (no recursive setTimeout)
 * - Pure scheduling layer — does not modify the preloadStore interface
 */

import { useEffect, useCallback, useRef } from 'react';
import { usePreloadStore } from '@/stores';

// ── Polling interval config ─────────────────────

/** High-frequency polling: Inbox / Agent Inbox */
const HIGH_FREQ_INTERVAL = 10_000; // 10s

/** Mid-frequency polling: Jobs / RAG Files / Awareness */
const MID_FREQ_INTERVAL = 30_000; // 30s

// ── Hook ────────────────────────────────────────

interface UseAutoRefreshOptions {
  agentId: string;
  userId: string;
}

/**
 * Smart auto-refresh hook
 *
 * Returns refreshAll() for callers to trigger a full data reload
 * (e.g. after agent execution completes).
 */
export function useAutoRefresh({ agentId, userId }: UseAutoRefreshOptions) {
  const {
    refreshInbox,
    refreshAgentInbox,
    refreshJobs,
    refreshRAGFiles,
    refreshAwareness,
    refreshChatHistory,
    refreshSocialNetwork,
  } = usePreloadStore();

  // Keep latest ids in refs so interval callbacks never capture stale values
  const agentIdRef = useRef(agentId);
  const userIdRef = useRef(userId);
  agentIdRef.current = agentId;
  userIdRef.current = userId;

  // ── Full refresh (call after agent execution, NOT silent — user sees loading) ──

  const refreshAll = useCallback(async () => {
    const aid = agentIdRef.current;
    const uid = userIdRef.current;
    if (!aid || !uid) return;

    await Promise.allSettled([
      refreshInbox(uid),
      refreshAgentInbox(aid),
      refreshJobs(aid),
      refreshRAGFiles(aid, uid),
      refreshAwareness(aid),
      refreshChatHistory(aid, uid),
      refreshSocialNetwork(aid),
    ]);
  }, [refreshInbox, refreshAgentInbox, refreshJobs, refreshRAGFiles, refreshAwareness, refreshChatHistory, refreshSocialNetwork]);

  // ── Polling scheduler (all polls are silent) ──

  useEffect(() => {
    if (!agentId || !userId) return;

    // High-freq tick: inbox + agentInbox (silent — no loading flicker, no re-render if unchanged)
    const tickHigh = () => {
      if (document.hidden) return;
      const aid = agentIdRef.current;
      const uid = userIdRef.current;
      if (!aid || !uid) return;
      refreshInbox(uid, true);
      refreshAgentInbox(aid, true);
    };

    // Mid-freq tick: jobs + ragFiles + awareness (silent)
    const tickMid = () => {
      if (document.hidden) return;
      const aid = agentIdRef.current;
      const uid = userIdRef.current;
      if (!aid || !uid) return;
      refreshJobs(aid, undefined, undefined, true);
      refreshRAGFiles(aid, uid, true);
      refreshAwareness(aid, true);
      refreshSocialNetwork(aid, true);
    };

    const highTimer = setInterval(tickHigh, HIGH_FREQ_INTERVAL);
    const midTimer = setInterval(tickMid, MID_FREQ_INTERVAL);

    // Refresh immediately when tab becomes visible again (also silent)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        tickHigh();
        tickMid();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(highTimer);
      clearInterval(midTimer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [agentId, userId, refreshInbox, refreshAgentInbox, refreshJobs, refreshRAGFiles, refreshAwareness, refreshSocialNetwork]);

  return { refreshAll };
}
