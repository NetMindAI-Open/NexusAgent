/**
 * Job Complex Store - manages the state of Job Complex dependency groups
 *
 * Features:
 * 1. Manage the currently viewed Job group
 * 2. Poll to refresh Job status
 * 3. Manage selected Job
 */

import { create } from 'zustand';
import { api } from '@/lib/api';
import type { JobNode, JobNodeStatus, JobTemplate } from '@/types/jobComplex';
import type { Job } from '@/types/api';

// Preset Templates
export const JOB_TEMPLATES: JobTemplate[] = [
  {
    id: 'company_analysis',
    name: 'Company Analysis',
    description: 'Analyze target company from financial, news, patent, and talent perspectives',
    icon: 'Building2',
    variables: [
      { name: 'company_name', label: 'Company Name', type: 'text', required: true },
    ],
    jobs: [
      {
        task_key: 'init',
        title: 'Define Analysis Dimensions',
        description: 'Determine which aspects to focus on for the target company',
        depends_on: [],
        payload_template: 'Define analysis dimensions for {{company_name}}',
      },
      {
        task_key: 'financial',
        title: 'Financial Data Analysis',
        description: 'Retrieve funding and valuation data',
        depends_on: ['init'],
        payload_template: 'Get funding and valuation data for {{company_name}}',
      },
      {
        task_key: 'news',
        title: 'News Sentiment Analysis',
        description: 'Search for recent related news',
        depends_on: ['init'],
        payload_template: 'Search recent news for {{company_name}}',
      },
      {
        task_key: 'patents',
        title: 'Patent Technology Analysis',
        description: 'Query patent applications',
        depends_on: ['init'],
        payload_template: 'Query patent applications for {{company_name}}',
      },
      {
        task_key: 'talent',
        title: 'Talent Trend Analysis',
        description: 'Analyze talent movement trends',
        depends_on: ['init'],
        payload_template: 'Analyze talent trends for {{company_name}}',
      },
      {
        task_key: 'report',
        title: 'Generate Comprehensive Report',
        description: 'Consolidate all data into an analysis report',
        depends_on: ['financial', 'news', 'patents', 'talent'],
        payload_template: 'Consolidate all data and generate analysis report for {{company_name}}',
      },
    ],
  },
  {
    id: 'pr_review',
    name: 'PR Impact Analysis',
    description: 'Multi-dimensional analysis of code changes impact and risks',
    icon: 'GitPullRequest',
    variables: [
      { name: 'pr_url', label: 'PR URL', type: 'text', required: true },
    ],
    jobs: [
      {
        task_key: 'fetch_pr',
        title: 'Fetch PR Information',
        description: 'Get PR basic info and code changes',
        depends_on: [],
        payload_template: 'Fetch PR information: {{pr_url}}',
      },
      {
        task_key: 'code_analysis',
        title: 'Code Quality Analysis',
        description: 'Analyze code change quality and style',
        depends_on: ['fetch_pr'],
        payload_template: 'Analyze code quality of {{pr_url}}',
      },
      {
        task_key: 'security_scan',
        title: 'Security Scan',
        description: 'Scan for potential security vulnerabilities',
        depends_on: ['fetch_pr'],
        payload_template: 'Scan security issues in {{pr_url}}',
      },
      {
        task_key: 'impact_analysis',
        title: 'Impact Scope Analysis',
        description: 'Analyze affected modules and dependencies',
        depends_on: ['fetch_pr'],
        payload_template: 'Analyze impact scope of {{pr_url}}',
      },
      {
        task_key: 'final_report',
        title: 'Review Report',
        description: 'Generate comprehensive review report and recommendations',
        depends_on: ['code_analysis', 'security_scan', 'impact_analysis'],
        payload_template: 'Generate comprehensive review report for {{pr_url}}',
      },
    ],
  },
  {
    id: 'content_publish',
    name: 'Multi-Platform Publishing',
    description: 'Adapt and publish content to multiple platforms',
    icon: 'Share2',
    variables: [
      { name: 'content', label: 'Original Content', type: 'text', required: true },
    ],
    jobs: [
      {
        task_key: 'parse_content',
        title: 'Parse Original Content',
        description: 'Parse and extract key points from content',
        depends_on: [],
        payload_template: 'Parse content: {{content}}',
      },
      {
        task_key: 'adapt_medium',
        title: 'Medium Adaptation',
        description: 'Adapt content for Medium format',
        depends_on: ['parse_content'],
        payload_template: 'Adapt content to Medium format',
      },
      {
        task_key: 'adapt_linkedin',
        title: 'LinkedIn Adaptation',
        description: 'Adapt content for LinkedIn format',
        depends_on: ['parse_content'],
        payload_template: 'Adapt content to LinkedIn format',
      },
      {
        task_key: 'adapt_devto',
        title: 'Dev.to Adaptation',
        description: 'Adapt content for Dev.to format',
        depends_on: ['parse_content'],
        payload_template: 'Adapt content to Dev.to format',
      },
      {
        task_key: 'publish_summary',
        title: 'Publishing Summary',
        description: 'Summarize publishing results across platforms',
        depends_on: ['adapt_medium', 'adapt_linkedin', 'adapt_devto'],
        payload_template: 'Summarize publishing results across platforms',
      },
    ],
  },
];

// Convert API Job to JobNode
function jobToJobNode(job: Job): JobNode {
  let depends_on: string[] = [];
  let task_key = job.job_id;

  if (job.payload) {
    try {
      const payload = JSON.parse(job.payload);
      if (payload.depends_on && Array.isArray(payload.depends_on)) {
        depends_on = payload.depends_on;
      }
      if (payload.task_key) {
        task_key = payload.task_key;
      }
    } catch {
      // Ignore parsing errors
    }
  }

  return {
    id: job.job_id,
    task_key,
    title: job.title,
    description: job.description,
    status: job.status as JobNodeStatus,
    depends_on,
    started_at: job.last_run_time,
    completed_at: job.status === 'completed' ? job.updated_at : undefined,
    output: job.process?.join('\n'),
  };
}

interface JobComplexState {
  // Current Job group
  jobs: JobNode[];
  groupId: string | null;

  // Selection state
  selectedJobId: string | null;

  // Polling state
  isPolling: boolean;
  pollingInterval: number; // ms - current actual interval (dynamically adjusted)
  pollTimerId: ReturnType<typeof setTimeout> | null;
  pollAttempt: number;     // Consecutive unchanged poll count (used for backoff calculation)

  // Loading state
  loading: boolean;
  error: string | null;

  // Methods
  loadJobs: (agentId: string, userId: string) => Promise<void>;
  selectJob: (jobId: string | null) => void;
  startPolling: (agentId: string, userId: string) => void;
  stopPolling: () => void;
  setPollingInterval: (interval: number) => void;
  clearJobs: () => void;
}

export const useJobComplexStore = create<JobComplexState>()((set, get) => ({
  // Initial state
  jobs: [],
  groupId: null,
  selectedJobId: null,
  isPolling: false,
  pollingInterval: 3000, // Base interval 3 seconds
  pollTimerId: null,
  pollAttempt: 0,
  loading: false,
  error: null,

  // Load Jobs
  loadJobs: async (agentId: string, userId: string) => {
    set({ loading: true, error: null });
    try {
      const result = await api.getJobs(agentId, userId);
      if (result.success) {
        const jobNodes = result.jobs.map(jobToJobNode);
        set({ jobs: jobNodes, loading: false });
      } else {
        set({ loading: false, error: result.error || 'Failed to load jobs' });
      }
    } catch (error) {
      set({ loading: false, error: String(error) });
    }
  },

  // Select Job
  selectJob: (jobId: string | null) => {
    set({ selectedJobId: jobId });
  },

  // Start polling (exponential backoff: fast poll on state change, gradual slowdown when unchanged)
  startPolling: (agentId: string, userId: string) => {
    const { isPolling } = get();
    if (isPolling) return;

    const BASE_INTERVAL = 3000;   // 3s
    const MAX_INTERVAL = 30000;   // 30s

    set({ isPolling: true, pollAttempt: 0 });

    const poll = async () => {
      const state = get();
      if (!state.isPolling) return;

      const prevSnapshot = JSON.stringify(state.jobs.map((j) => j.status));
      await state.loadJobs(agentId, userId);

      const curr = get();
      if (!curr.isPolling) return;

      // Check if all Jobs are finished
      const allDone = curr.jobs.every(
        (j) => j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled'
      );
      if (allDone && curr.jobs.length > 0) {
        curr.stopPolling();
        return;
      }

      // Exponential backoff: change detected -> reset counter; no change -> increment
      const currSnapshot = JSON.stringify(curr.jobs.map((j) => j.status));
      const changed = currSnapshot !== prevSnapshot;
      const nextAttempt = changed ? 0 : curr.pollAttempt + 1;
      const delay = Math.min(BASE_INTERVAL * Math.pow(1.5, nextAttempt), MAX_INTERVAL);

      const timerId = setTimeout(poll, delay);
      set({ pollTimerId: timerId, pollAttempt: nextAttempt });
    };

    poll();
  },

  // Stop polling
  stopPolling: () => {
    const { pollTimerId } = get();
    if (pollTimerId) {
      clearTimeout(pollTimerId);
    }
    set({ isPolling: false, pollTimerId: null });
  },

  // Set polling interval
  setPollingInterval: (interval: number) => {
    set({ pollingInterval: interval });
  },

  // Clear all
  clearJobs: () => {
    const { pollTimerId } = get();
    if (pollTimerId) {
      clearTimeout(pollTimerId);
    }
    set({
      jobs: [],
      groupId: null,
      selectedJobId: null,
      isPolling: false,
      pollTimerId: null,
      pollAttempt: 0,
      loading: false,
      error: null,
    });
  },
}));
