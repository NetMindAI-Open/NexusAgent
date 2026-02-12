/**
 * Job Dependency Graph - Visualize job dependencies using React Flow
 *
 * Features:
 * 1. Automatic topological layout (left to right)
 * 2. Node colors change based on status
 * 3. Animated edges for running jobs
 * 4. Click nodes to show details
 */

import { useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';

import type { JobNode, JobNodeStatus } from '@/types/jobComplex';

interface JobDependencyGraphProps {
  jobs: JobNode[];
  onNodeClick?: (jobId: string) => void;
  selectedJobId?: string | null;
}

// Node color configuration
const statusColors: Record<JobNodeStatus, { bg: string; border: string; text: string }> = {
  pending: { bg: '#f3f4f6', border: '#9ca3af', text: '#6b7280' },
  active: { bg: '#dbeafe', border: '#3b82f6', text: '#1d4ed8' },
  running: { bg: '#fef3c7', border: '#f59e0b', text: '#b45309' },
  completed: { bg: '#d1fae5', border: '#10b981', text: '#047857' },
  failed: { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c' },
  cancelled: { bg: '#e5e7eb', border: '#6b7280', text: '#4b5563' },
};

// Status display labels
const statusLabels: Record<JobNodeStatus, string> = {
  pending: 'Pending',
  active: 'Active',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

// Calculate topological level
function getTopologicalLevel(job: JobNode, allJobs: JobNode[], memo: Map<string, number> = new Map()): number {
  if (memo.has(job.id)) {
    return memo.get(job.id)!;
  }

  if (job.depends_on.length === 0) {
    memo.set(job.id, 0);
    return 0;
  }

  const depLevels = job.depends_on
    .map((depKey) => {
      const dep = allJobs.find((j) => j.task_key === depKey || j.id === depKey);
      return dep ? getTopologicalLevel(dep, allJobs, memo) : null;
    })
    .filter((level): level is number => level !== null);

  // If no valid dependencies found, return level 0
  const level = depLevels.length > 0 ? Math.max(...depLevels) + 1 : 0;
  memo.set(job.id, level);
  return level;
}

// Calculate node positions (auto layout)
function calculatePositions(jobs: JobNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const memo = new Map<string, number>();

  // Group by level
  const levels: Map<number, JobNode[]> = new Map();
  jobs.forEach((job) => {
    const level = getTopologicalLevel(job, jobs, memo);
    if (!levels.has(level)) {
      levels.set(level, []);
    }
    levels.get(level)!.push(job);
  });

  // Calculate positions
  const horizontalSpacing = 220;
  const verticalSpacing = 100;

  levels.forEach((levelJobs, level) => {
    const startY = -((levelJobs.length - 1) * verticalSpacing) / 2;
    levelJobs.forEach((job, index) => {
      positions.set(job.id, {
        x: level * horizontalSpacing,
        y: startY + index * verticalSpacing,
      });
    });
  });

  return positions;
}

export function JobDependencyGraph({ jobs, onNodeClick, selectedJobId }: JobDependencyGraphProps) {
  // Convert to React Flow format
  const { initialNodes, initialEdges } = useMemo(() => {
    // Safety check: ensure jobs is a valid array
    if (!Array.isArray(jobs) || jobs.length === 0) {
      return { initialNodes: [], initialEdges: [] };
    }

    try {
      const positions = calculatePositions(jobs);

      const nodes: Node[] = jobs.map((job) => {
        const pos = positions.get(job.id) || { x: 0, y: 0 };
        const colors = statusColors[job.status] || statusColors.pending;
        const isSelected = selectedJobId === job.id;

        return {
          id: job.id,
          type: 'default',
          data: {
            label: (
              <div className="text-center px-1">
                <div className="font-medium text-sm truncate" style={{ color: colors.text }}>
                  {job.title || 'Untitled Job'}
                </div>
                <div className="text-xs opacity-75 mt-0.5">
                  {statusLabels[job.status] || job.status}
                </div>
              </div>
            ),
          },
          position: pos,
          style: {
            background: colors.bg,
            border: `2px solid ${isSelected ? '#6366f1' : colors.border}`,
            borderRadius: 8,
            padding: '8px 12px',
            minWidth: 120,
            boxShadow: isSelected ? '0 0 0 2px rgba(99, 102, 241, 0.3)' : 'none',
          },
        };
      });

      const edges: Edge[] = jobs.flatMap((job) => {
        if (!job.depends_on || !Array.isArray(job.depends_on)) {
          return [];
        }

        return job.depends_on
          .map((depKey) => {
            const sourceJob = jobs.find((j) => j.task_key === depKey || j.id === depKey);
            if (!sourceJob) return null;

            const isActive = job.status === 'running' || job.status === 'active';

            return {
              id: `${sourceJob.id}-${job.id}`,
              source: sourceJob.id,
              target: job.id,
              animated: isActive,
              style: {
                stroke: isActive ? '#f59e0b' : '#94a3b8',
                strokeWidth: isActive ? 2 : 1,
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: isActive ? '#f59e0b' : '#94a3b8',
              },
            } as Edge;
          })
          .filter((edge) => edge !== null) as Edge[];
      });

      return { initialNodes: nodes, initialEdges: edges };
    } catch (error) {
      console.error('Error calculating graph layout:', error);
      return { initialNodes: [], initialEdges: [] };
    }
  }, [jobs, selectedJobId]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-tertiary)]">
        No jobs with dependencies
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[300px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={2}
        attributionPosition="bottom-left"
      >
        <Background color="#e5e7eb" gap={16} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            try {
              const job = jobs.find((j) => j.id === node.id);
              if (job && statusColors[job.status]) {
                return statusColors[job.status].border;
              }
              return '#9ca3af';
            } catch {
              return '#9ca3af';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  );
}
