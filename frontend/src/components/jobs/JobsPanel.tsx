/**
 * Jobs Panel - Task management panel
 * Bioluminescent Terminal style - Deep ocean aesthetics
 * Enhanced with Control Center Dashboard design
 *
 * Supports three view modes:
 * 1. List view - Traditional job list
 * 2. Graph view - React Flow dependency visualization
 * 3. Timeline view - Gantt chart style execution timeline
 */

import { useState, useMemo } from 'react';
import {
  Clock,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  RefreshCw,
  Calendar,
  Ban,
  Loader2,
  List,
  GitBranch,
  GanttChartSquare,
  Zap,
  TrendingUp,
  AlertCircle,
  Users,
  FileText,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from '@/components/ui';
import { useConfigStore, usePreloadStore } from '@/stores';
import { cn, formatRelativeTime } from '@/lib/utils';
import { api } from '@/lib/api';
import { JobDependencyGraph } from './JobDependencyGraph';
import { JobExecutionTimeline } from './JobExecutionTimeline';
import { JobDetailPanel } from './JobDetailPanel';
import type { JobNode, JobNodeStatus } from '@/types/jobComplex';
import type { Job } from '@/types/api';

type ViewMode = 'list' | 'graph' | 'timeline';

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
  color?: 'accent' | 'success' | 'warning' | 'error' | 'secondary';
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
    error: {
      bg: 'bg-[var(--color-error)]/10',
      icon: 'text-[var(--color-error)]',
      value: 'text-[var(--color-error)]',
      glow: 'shadow-[0_0_15px_rgba(239,68,68,0.2)]',
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

// Status Distribution Bar
function StatusDistributionBar({ jobs }: { jobs: Job[] }) {
  const stats = useMemo(() => {
    const counts = {
      completed: jobs.filter((j) => j.status === 'completed').length,
      running: jobs.filter((j) => j.status === 'running').length,
      active: jobs.filter((j) => j.status === 'active').length,
      paused: jobs.filter((j) => j.status === 'paused').length,
      pending: jobs.filter((j) => j.status === 'pending').length,
      failed: jobs.filter((j) => j.status === 'failed').length,
      cancelled: jobs.filter((j) => j.status === 'cancelled').length,
    };
    return counts;
  }, [jobs]);

  const total = jobs.length || 1;

  if (jobs.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[9px] font-mono text-[var(--text-tertiary)]">
        <span>Status Distribution</span>
        <span>{jobs.length} total</span>
      </div>
      <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden flex">
        {stats.completed > 0 && (
          <div
            className="bg-[var(--color-success)] transition-all duration-500"
            style={{ width: `${(stats.completed / total) * 100}%` }}
            title={`Completed: ${stats.completed}`}
          />
        )}
        {stats.running > 0 && (
          <div
            className="bg-[var(--color-warning)] transition-all duration-500"
            style={{ width: `${(stats.running / total) * 100}%` }}
            title={`Running: ${stats.running}`}
          />
        )}
        {stats.active > 0 && (
          <div
            className="bg-[var(--accent-primary)] transition-all duration-500"
            style={{ width: `${(stats.active / total) * 100}%` }}
            title={`Active: ${stats.active}`}
          />
        )}
        {stats.paused > 0 && (
          <div
            className="bg-[var(--accent-secondary)] transition-all duration-500"
            style={{ width: `${(stats.paused / total) * 100}%` }}
            title={`Paused: ${stats.paused}`}
          />
        )}
        {stats.pending > 0 && (
          <div
            className="bg-[var(--text-tertiary)] transition-all duration-500"
            style={{ width: `${(stats.pending / total) * 100}%` }}
            title={`Pending: ${stats.pending}`}
          />
        )}
        {stats.failed > 0 && (
          <div
            className="bg-[var(--color-error)] transition-all duration-500"
            style={{ width: `${(stats.failed / total) * 100}%` }}
            title={`Failed: ${stats.failed}`}
          />
        )}
        {stats.cancelled > 0 && (
          <div
            className="bg-[var(--bg-tertiary)] transition-all duration-500"
            style={{ width: `${(stats.cancelled / total) * 100}%` }}
            title={`Cancelled: ${stats.cancelled}`}
          />
        )}
      </div>
      <div className="flex flex-wrap gap-2 text-[8px] font-mono">
        {stats.completed > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
            <span className="text-[var(--text-tertiary)]">{stats.completed} completed</span>
          </span>
        )}
        {stats.running > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--color-warning)]" />
            <span className="text-[var(--text-tertiary)]">{stats.running} running</span>
          </span>
        )}
        {stats.active > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)]" />
            <span className="text-[var(--text-tertiary)]">{stats.active} active</span>
          </span>
        )}
        {stats.paused > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-secondary)]" />
            <span className="text-[var(--text-tertiary)]">{stats.paused} paused</span>
          </span>
        )}
        {stats.failed > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--color-error)]" />
            <span className="text-[var(--text-tertiary)]">{stats.failed} failed</span>
          </span>
        )}
      </div>
    </div>
  );
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; bgColor: string; label: string }> = {
  pending: { icon: Clock, color: 'text-[var(--text-tertiary)]', bgColor: 'bg-[var(--bg-tertiary)]', label: 'Pending' },
  active: { icon: Zap, color: 'text-[var(--accent-primary)]', bgColor: 'bg-[var(--accent-glow)]', label: 'Active' },
  running: { icon: Play, color: 'text-[var(--color-warning)]', bgColor: 'bg-[var(--color-warning)]/10', label: 'Running' },
  paused: { icon: Pause, color: 'text-[var(--accent-secondary)]', bgColor: 'bg-[var(--accent-secondary)]/10', label: 'Paused' },
  completed: { icon: CheckCircle, color: 'text-[var(--color-success)]', bgColor: 'bg-[var(--color-success)]/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-[var(--color-error)]', bgColor: 'bg-[var(--color-error)]/10', label: 'Failed' },
  cancelled: { icon: Ban, color: 'text-[var(--text-tertiary)]', bgColor: 'bg-[var(--bg-tertiary)]', label: 'Cancelled' },
};

// Convert API Job to JobNode format
function jobToJobNode(job: Job): JobNode {
  // Prefer API-returned depends_on, fall back to parsing from payload
  let depends_on: string[] = job.depends_on || [];

  // If API did not return depends_on, try parsing from payload (backward compatibility)
  if (depends_on.length === 0 && job.payload) {
    try {
      const payload = JSON.parse(job.payload);
      if (payload.depends_on && Array.isArray(payload.depends_on)) {
        depends_on = payload.depends_on;
      }
    } catch {
      // Ignore parsing errors
    }
  }

  return {
    id: job.instance_id || job.job_id,  // Use instance_id as node ID (matches dependency relations)
    task_key: job.instance_id || job.job_id,
    title: job.title,
    description: job.description,
    status: job.status as JobNodeStatus,
    depends_on,
    started_at: job.last_run_time,
    completed_at: job.status === 'completed' ? job.updated_at : undefined,
    output: job.process?.join('\n'),
  };
}

export function JobsPanel() {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);

  const { agentId, userId } = useConfigStore();
  const {
    jobs: allJobs,
    jobsLoading: loading,
    refreshJobs,
  } = usePreloadStore();

  // Filter Jobs
  const jobs = statusFilter === 'all'
    ? allJobs
    : allJobs.filter((job) => job.status === statusFilter);

  // Convert to JobNode format (for graph and timeline)
  const jobNodes: JobNode[] = useMemo(() => jobs.map(jobToJobNode), [jobs]);

  // Get selected job details
  const selectedJob = useMemo(
    () => jobNodes.find((j) => j.id === selectedJobId) || null,
    [jobNodes, selectedJobId]
  );

  // Check if any jobs have dependencies
  const hasJobsWithDependencies = useMemo(
    () => jobNodes.some((j) => j.depends_on.length > 0),
    [jobNodes]
  );

  // Calculate job metrics
  const jobMetrics = useMemo(() => {
    const completed = allJobs.filter((j) => j.status === 'completed').length;
    const running = allJobs.filter((j) => j.status === 'running' || j.status === 'active').length;
    const failed = allJobs.filter((j) => j.status === 'failed').length;
    const successRate = allJobs.length > 0 ? Math.round((completed / (completed + failed || 1)) * 100) : 0;
    return { completed, running, failed, successRate };
  }, [allJobs]);

  const handleRefresh = () => {
    refreshJobs(agentId, userId);
  };

  const handleCancelJob = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();

    if (!confirm('Are you sure you want to cancel this job? This action cannot be undone.')) {
      return;
    }

    setCancellingJobId(jobId);
    try {
      const res = await api.cancelJob(jobId);
      if (res.success) {
        refreshJobs(agentId, userId);
      } else {
        alert(res.error || 'Failed to cancel job');
      }
    } catch (err) {
      console.error('Cancel job error:', err);
      alert('Failed to cancel job. Please try again.');
    } finally {
      setCancellingJobId(null);
    }
  };

  const canCancel = (status: string) => {
    return ['pending', 'active', 'running'].includes(status);
  };

  return (
    <Card variant="glass" className="flex flex-col h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[var(--color-warning)]/10 flex items-center justify-center">
            <Calendar className="w-4 h-4 text-[var(--color-warning)]" />
          </div>
          <span>Jobs</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant={allJobs.length > 0 ? 'accent' : 'default'} className="font-mono">
            {allJobs.length}
          </Badge>
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
      {allJobs.length > 0 && (
        <div className="px-4 pb-3 space-y-3">
          <div className="grid grid-cols-4 gap-2">
            <KPICard
              label="Active"
              value={jobMetrics.running}
              icon={Zap}
              color="warning"
              pulse={jobMetrics.running > 0}
              subtext="In progress"
            />
            <KPICard
              label="Success"
              value={jobMetrics.completed}
              icon={CheckCircle}
              color="success"
              subtext="Completed"
            />
            <KPICard
              label="Failed"
              value={jobMetrics.failed}
              icon={AlertCircle}
              color={jobMetrics.failed > 0 ? 'error' : 'secondary'}
              subtext="Errors"
            />
            <KPICard
              label="Rate"
              value={`${jobMetrics.successRate}%`}
              icon={TrendingUp}
              color="accent"
              subtext="Success rate"
            />
          </div>
          <StatusDistributionBar jobs={allJobs} />
        </div>
      )}

      {/* View Mode Tabs */}
      <div className="px-4 pb-3 flex gap-1 border-b border-[var(--border-subtle)]">
        {[
          { mode: 'list' as const, icon: List, label: 'List' },
          { mode: 'graph' as const, icon: GitBranch, label: 'Graph' },
          { mode: 'timeline' as const, icon: GanttChartSquare, label: 'Timeline' },
        ].map(({ mode, icon: Icon, label }) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-2 text-xs rounded-xl transition-all duration-300 font-medium',
              viewMode === mode
                ? 'bg-[var(--accent-primary)] text-[var(--bg-deep)] shadow-[0_0_15px_var(--accent-glow)]'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]'
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Status Filter (only for list view) */}
      {viewMode === 'list' && (
        <div className="px-4 py-2 flex gap-1.5 overflow-x-auto">
          {(['all', 'active', 'running', 'paused', 'pending', 'completed', 'failed', 'cancelled'] as const).map((status) => {
            const config = status !== 'all' ? statusConfig[status] : null;
            return (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={cn(
                  'px-3 py-1.5 text-[10px] rounded-lg transition-all duration-300 whitespace-nowrap font-mono uppercase tracking-wider',
                  statusFilter === status
                    ? 'bg-[var(--accent-glow)] text-[var(--accent-primary)] border border-[var(--accent-primary)]/30'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] border border-transparent'
                )}
              >
                {status === 'all' ? 'All' : config?.label}
              </button>
            );
          })}
        </div>
      )}

      <CardContent className="flex-1 overflow-hidden min-h-0">
        {/* List View */}
        {viewMode === 'list' && (
          <div className="h-full overflow-y-auto space-y-3 py-2">
            {jobs.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-14 h-14 rounded-2xl bg-[var(--color-warning)]/10 mx-auto mb-4 flex items-center justify-center">
                    <Calendar className="w-7 h-7 text-[var(--color-warning)]" />
                  </div>
                  <p className="text-[var(--text-secondary)] text-sm font-medium mb-1">No jobs found</p>
                  <p className="text-[var(--text-tertiary)] text-xs">Create a job to get started</p>
                </div>
              </div>
            ) : (
              jobs.map((job) => {
                const config = statusConfig[job.status] || statusConfig.pending;
                const StatusIcon = config.icon;
                const isExpanded = expandedId === job.job_id;
                const isCancelling = cancellingJobId === job.job_id;

                return (
                  <button
                    key={job.job_id}
                    onClick={() => setExpandedId(isExpanded ? null : job.job_id)}
                    className={cn(
                      'w-full text-left p-4 rounded-xl transition-all duration-300 group',
                      'border bg-[var(--bg-elevated)]',
                      isExpanded
                        ? 'border-[var(--accent-primary)]/30 shadow-[0_0_20px_var(--accent-glow)]'
                        : 'border-[var(--border-subtle)] hover:border-[var(--accent-primary)]/20 hover:shadow-lg',
                      job.status === 'running' && 'bg-[var(--color-warning)]/5 border-[var(--color-warning)]/30',
                      job.status === 'cancelled' && 'opacity-60'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-300',
                        config.bgColor,
                        job.status === 'running' && 'animate-pulse'
                      )}>
                        <StatusIcon className={cn('w-4 h-4', config.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className={cn(
                            'text-sm font-semibold truncate transition-colors',
                            job.status === 'cancelled'
                              ? 'text-[var(--text-tertiary)] line-through'
                              : 'text-[var(--text-primary)] group-hover:text-[var(--accent-primary)]'
                          )}>
                            {job.title}
                          </span>
                          <Badge
                            variant={
                              job.status === 'running'
                                ? 'warning'
                                : job.status === 'completed'
                                ? 'success'
                                : job.status === 'failed'
                                ? 'error'
                                : job.status === 'active'
                                ? 'accent'
                                : job.status === 'paused'
                                ? 'outline'
                                : 'default'
                            }
                            size="sm"
                            glow={job.status === 'running' || job.status === 'active'}
                          >
                            {config.label}
                          </Badge>
                        </div>

                        {job.description && (
                          <p className="text-xs text-[var(--text-tertiary)] mt-1.5 line-clamp-1">
                            {job.description}
                          </p>
                        )}

                        {isExpanded && (
                          <div className="mt-4 space-y-3 text-xs animate-fade-in">
                            <div className="grid grid-cols-2 gap-3 p-3 bg-[var(--bg-sunken)] rounded-lg border border-[var(--border-subtle)] font-mono">
                              <div>
                                <span className="text-[var(--text-tertiary)]">Type:</span>{' '}
                                <span className="text-[var(--accent-primary)]">
                                  {job.job_type}
                                </span>
                              </div>
                              {job.trigger_config?.trigger_type && (
                                <div>
                                  <span className="text-[var(--text-tertiary)]">Trigger:</span>{' '}
                                  <span className="text-[var(--accent-secondary)]">
                                    {job.trigger_config.trigger_type}
                                  </span>
                                </div>
                              )}
                              {job.next_run_time && (
                                <div className="col-span-2">
                                  <span className="text-[var(--text-tertiary)]">Next run:</span>{' '}
                                  <span className="text-[var(--color-success)]">
                                    {formatRelativeTime(job.next_run_time)}
                                  </span>
                                </div>
                              )}
                              {job.last_run_time && (
                                <div className="col-span-2">
                                  <span className="text-[var(--text-tertiary)]">Last run:</span>{' '}
                                  <span className="text-[var(--text-secondary)]">
                                    {formatRelativeTime(job.last_run_time)}
                                  </span>
                                </div>
                              )}
                              {job.last_error && (
                                <div className="col-span-2 p-2 bg-[var(--color-error)]/10 rounded-lg border border-[var(--color-error)]/20">
                                  <span className="text-[var(--color-error)] font-medium">Error:</span>{' '}
                                  <span className="text-[var(--text-secondary)]">
                                    {job.last_error}
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Target User - Execution Identity */}
                            {job.related_entity_id && (
                              <div className="p-3 bg-[var(--accent-primary)]/5 rounded-lg border border-[var(--accent-primary)]/20">
                                <div className="text-[9px] text-[var(--accent-primary)] font-medium uppercase tracking-wider flex items-center gap-1.5 mb-2">
                                  <Users className="w-3 h-3" />
                                  Target User (Execution Identity)
                                </div>
                                <span
                                  className="inline-flex items-center px-2 py-1 text-[9px] rounded-lg bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/20 font-mono"
                                  title={job.related_entity_id}
                                >
                                  {job.related_entity_id.length > 20 ? `${job.related_entity_id.slice(0, 20)}...` : job.related_entity_id}
                                </span>
                              </div>
                            )}

                            {/* Linked Narrative - Associated conversation context */}
                            {job.narrative_id && (
                              <div className="p-3 bg-[var(--accent-secondary)]/5 rounded-lg border border-[var(--accent-secondary)]/20">
                                <div className="text-[9px] text-[var(--accent-secondary)] font-medium uppercase tracking-wider flex items-center gap-1.5 mb-2">
                                  <FileText className="w-3 h-3" />
                                  Linked Narrative
                                </div>
                                <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                                  {job.narrative_id}
                                </span>
                              </div>
                            )}

                            {canCancel(job.status) && (
                              <div className="pt-3 border-t border-[var(--border-subtle)]">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => handleCancelJob(e, job.job_id)}
                                  disabled={isCancelling}
                                  className="text-[var(--color-error)] hover:bg-[var(--color-error)]/10 hover:shadow-[0_0_10px_var(--color-error)/20]"
                                >
                                  {isCancelling ? (
                                    <>
                                      <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                                      Cancelling...
                                    </>
                                  ) : (
                                    <>
                                      <Ban className="w-3 h-3 mr-1.5" />
                                      Cancel Job
                                    </>
                                  )}
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        )}

        {/* Graph View */}
        {viewMode === 'graph' && (
          <div className="h-full flex flex-col">
            {!hasJobsWithDependencies ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                <div className="w-16 h-16 rounded-2xl bg-[var(--accent-secondary)]/10 mx-auto mb-4 flex items-center justify-center">
                  <GitBranch className="w-8 h-8 text-[var(--accent-secondary)]" />
                </div>
                <p className="text-[var(--text-secondary)] text-sm font-medium mb-1">
                  No dependency relationships
                </p>
                <p className="text-[var(--text-tertiary)] text-xs">
                  Jobs with dependencies will be visualized here
                </p>
              </div>
            ) : (
              <>
                <div className="flex-1 min-h-[300px] rounded-xl overflow-hidden border border-[var(--border-subtle)]">
                  <JobDependencyGraph
                    jobs={jobNodes}
                    onNodeClick={setSelectedJobId}
                    selectedJobId={selectedJobId}
                  />
                </div>
                {selectedJob && (
                  <div className="border-t border-[var(--border-subtle)] mt-3">
                    <JobDetailPanel
                      job={selectedJob}
                      onClose={() => setSelectedJobId(null)}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Timeline View */}
        {viewMode === 'timeline' && (
          <div className="h-full flex flex-col">
            {jobs.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-16 h-16 rounded-2xl bg-[var(--accent-primary)]/10 mx-auto mb-4 flex items-center justify-center">
                    <GanttChartSquare className="w-8 h-8 text-[var(--accent-primary)]" />
                  </div>
                  <p className="text-[var(--text-secondary)] text-sm font-medium mb-1">No jobs to display</p>
                  <p className="text-[var(--text-tertiary)] text-xs">Create jobs to see the timeline</p>
                </div>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto p-2">
                  <JobExecutionTimeline
                    jobs={jobNodes}
                    onJobClick={setSelectedJobId}
                    selectedJobId={selectedJobId}
                  />
                </div>
                {selectedJob && (
                  <div className="border-t border-[var(--border-subtle)] mt-2">
                    <JobDetailPanel
                      job={selectedJob}
                      onClose={() => setSelectedJobId(null)}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default JobsPanel;
