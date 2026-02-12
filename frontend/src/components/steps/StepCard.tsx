/**
 * Step Card component - Bioluminescent Terminal style
 * Individual execution step with dramatic visual effects
 *
 * User-friendly display of execution steps, supports the following data structures:
 * - display: { summary, items: [{icon, name, desc/time/preview}], hint }
 * - execution: { icon, text }
 * - result_summary: Tool execution result summary
 * - selection_reason / decision_reasoning: LLM decision reasoning
 * - relationship_graph: Mermaid relationship graph
 */

import { CheckCircle2, Loader2, XCircle, ChevronDown, ChevronRight, Brain, GitBranch, FileText } from 'lucide-react';
import { useState } from 'react';
import type { Step } from '@/types';
import { cn } from '@/lib/utils';

interface StepCardProps {
  step: Step;
  isLast: boolean;
}

// Display data type definitions
interface NarrativeItem {
  id?: string;
  name: string;
  time?: string;
  summary?: string;
  score?: number;
}

interface InstanceItem {
  icon?: string;
  instance_id?: string;
  module?: string;
  status?: string;
  desc?: string;
}

interface DisplayData {
  summary?: string;
  items?: (NarrativeItem | InstanceItem)[];
}

interface ExecutionDisplay {
  icon?: string;
  text?: string;
  desc?: string;
}

// Decision reasoning component
function ReasoningBlock({ title, reason, icon: Icon }: { title: string; reason: string; icon?: React.ComponentType<{ className?: string }> }) {
  const IconComponent = Icon || Brain;
  return (
    <div className="mt-3 p-3 rounded-xl bg-[var(--bg-sunken)] border border-[var(--border-subtle)]">
      <div className="flex items-center gap-2 text-[10px] text-[var(--text-tertiary)] mb-2 uppercase tracking-wider font-mono">
        <IconComponent className="w-3 h-3 text-[var(--accent-primary)]" />
        <span>{title}</span>
      </div>
      <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
        {reason}
      </p>
    </div>
  );
}

// Relationship graph component
function RelationshipGraph({ graph }: { graph: string }) {
  if (!graph) return null;

  return (
    <div className="mt-3 p-3 rounded-xl bg-[var(--bg-sunken)] border border-[var(--border-subtle)]">
      <div className="flex items-center gap-2 text-[10px] text-[var(--text-tertiary)] mb-2 uppercase tracking-wider font-mono">
        <GitBranch className="w-3 h-3 text-[var(--accent-secondary)]" />
        <span>Module Relationship Graph</span>
      </div>
      <pre className="text-[10px] text-[var(--text-secondary)] font-mono overflow-x-auto whitespace-pre-wrap">
        {graph}
      </pre>
    </div>
  );
}

// Changes summary component
function ChangesSummary({ changes }: { changes: { added?: string[]; removed?: string[]; updated?: string[]; kept?: string[] } }) {
  const hasChanges = changes && (
    (changes.added?.length ?? 0) > 0 ||
    (changes.removed?.length ?? 0) > 0 ||
    (changes.updated?.length ?? 0) > 0
  );

  if (!hasChanges) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-mono">
      {changes.added && changes.added.length > 0 && (
        <span className="px-2 py-0.5 rounded-full bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/30">
          +{changes.added.length} added
        </span>
      )}
      {changes.removed && changes.removed.length > 0 && (
        <span className="px-2 py-0.5 rounded-full bg-[var(--color-error)]/10 text-[var(--color-error)] border border-[var(--color-error)]/30">
          -{changes.removed.length} removed
        </span>
      )}
      {changes.updated && changes.updated.length > 0 && (
        <span className="px-2 py-0.5 rounded-full bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/30">
          ~{changes.updated.length} updated
        </span>
      )}
    </div>
  );
}

export function StepCard({ step, isLast }: StepCardProps) {
  const [expanded, setExpanded] = useState(step.status === 'running');

  const StatusIcon = {
    running: Loader2,
    completed: CheckCircle2,
    failed: XCircle,
  }[step.status];

  const statusColor = {
    running: 'text-[var(--accent-primary)]',
    completed: 'text-[var(--color-success)]',
    failed: 'text-[var(--color-error)]',
  }[step.status];

  const borderColor = {
    running: 'border-l-[var(--accent-primary)]',
    completed: 'border-l-[var(--color-success)]',
    failed: 'border-l-[var(--color-error)]',
  }[step.status];

  const bgColor = {
    running: 'bg-[var(--accent-glow)]',
    completed: 'bg-transparent',
    failed: 'bg-[var(--color-error)]/5',
  }[step.status];

  // Extract user-friendly display data from details
  const displayData = step.details?.display as DisplayData | undefined;
  const executionData = step.details?.execution as ExecutionDisplay | undefined;

  // Extract decision reasoning and details
  const selectionReason = step.details?.selection_reason as string | undefined;
  const selectionMethod = step.details?.selection_method as string | undefined;
  const retrievalMethod = step.details?.retrieval_method as string | undefined;
  const decisionReasoning = step.details?.decision_reasoning as string | undefined;
  const changesSummary = step.details?.changes_summary as { added?: string[]; removed?: string[]; updated?: string[]; kept?: string[] } | undefined;
  const relationshipGraph = step.details?.relationship_graph as string | undefined;

  // Check if there is expandable content
  const hasExpandableContent = step.substeps.length > 0 ||
    displayData?.items?.length ||
    executionData ||
    selectionReason ||
    decisionReasoning ||
    relationshipGraph;

  return (
    <div
      className={cn(
        'relative pl-4 border-l-2 transition-all duration-300',
        borderColor,
        bgColor,
        step.status === 'running' && '-ml-2 pl-6 py-3 rounded-xl border border-[var(--accent-primary)]/20 shadow-[0_0_20px_var(--accent-glow)]',
        step.status === 'completed' && 'opacity-80 hover:opacity-100'
      )}
    >
      {/* Connector line */}
      {!isLast && (
        <div className={cn(
          "absolute left-[-1px] top-full w-0.5 h-4 transition-all duration-500",
          step.status === 'completed' ? 'bg-[var(--color-success)]/50' : 'bg-[var(--border-default)]'
        )} />
      )}

      {/* Running pulse effect */}
      {step.status === 'running' && (
        <div className="absolute inset-0 rounded-xl animate-breathe bg-gradient-to-r from-[var(--accent-glow)] to-transparent pointer-events-none" />
      )}

      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 text-left group relative z-10"
      >
        <div className={cn(
          'relative',
          step.status === 'running' && 'animate-float'
        )}>
          <StatusIcon
            className={cn(
              'w-4 h-4 mt-0.5 shrink-0 transition-all duration-300',
              statusColor,
              step.status === 'running' && 'animate-spin'
            )}
          />
          {step.status === 'running' && (
            <div className="absolute inset-0 animate-ping opacity-30">
              <StatusIcon className={cn('w-4 h-4', statusColor)} />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-[var(--accent-primary)] bg-[var(--accent-glow)] px-1.5 py-0.5 rounded">
              {step.step}
            </span>
            <span className={cn(
              'text-sm font-medium truncate transition-colors',
              step.status === 'running' ? 'text-[var(--accent-primary)]' : 'text-[var(--text-primary)]'
            )}>
              {step.title}
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-1">
            {step.description}
          </p>
        </div>

        {hasExpandableContent && (
          <span className={cn(
            'text-[var(--text-tertiary)] transition-all duration-200',
            'group-hover:text-[var(--accent-primary)]',
            expanded && 'text-[var(--accent-primary)]'
          )}>
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        )}
      </button>

      {/* Expanded content */}
      {expanded && hasExpandableContent && (
        <div className="mt-3 ml-7 space-y-2 animate-fade-in">
          {/* Display items - Narratives or Instances (filtered out cancelled/archived) */}
          {displayData?.items && displayData.items.length > 0 && (
            <div className="space-y-2 font-mono text-xs">
              {displayData.items
                .filter((item) => {
                  // If it's an Instance, filter out cancelled and archived status
                  const instItem = item as InstanceItem;
                  if (instItem.status === 'cancelled' || instItem.status === 'archived') {
                    return false;
                  }
                  return true;
                })
                .map((item, i) => {
                // Determine if it's a Narrative or Instance
                const isInstance = 'instance_id' in item || 'module' in item;
                const instItem = item as InstanceItem;
                const narItem = item as NarrativeItem;

                return (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-[var(--text-secondary)] p-2 rounded-lg bg-[var(--bg-sunken)] border border-[var(--border-subtle)]"
                  >
                    {/* Icon (for instances) */}
                    {isInstance && instItem.icon && (
                      <span className="shrink-0 text-base">{instItem.icon}</span>
                    )}
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {isInstance ? (
                        // Instance display
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[var(--text-primary)] font-medium">
                            {instItem.module}
                          </span>
                          {instItem.instance_id && (
                            <span className="text-[var(--text-tertiary)]">
                              [{instItem.instance_id}]
                            </span>
                          )}
                          {instItem.status && (
                            <span className={cn(
                              "px-1.5 py-0.5 rounded-full text-[9px] font-medium",
                              instItem.status === 'active' && "bg-[var(--color-success)]/10 text-[var(--color-success)]",
                              instItem.status !== 'active' && "bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]"
                            )}>
                              {instItem.status}
                            </span>
                          )}
                        </div>
                      ) : (
                        // Narrative display
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            {narItem.id && (
                              <span className="text-[var(--accent-primary)]">
                                {narItem.id}
                              </span>
                            )}
                            {narItem.score !== undefined && (
                              <span className={cn(
                                "px-1.5 py-0.5 rounded-full text-[9px] font-medium",
                                narItem.score >= 0.8 && "bg-[var(--color-success)]/10 text-[var(--color-success)]",
                                narItem.score >= 0.5 && narItem.score < 0.8 && "bg-[var(--color-warning)]/10 text-[var(--color-warning)]",
                                narItem.score < 0.5 && "bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]"
                              )}>
                                {narItem.score.toFixed(3)}
                              </span>
                            )}
                            <span className="text-[var(--text-primary)] font-medium">
                              {narItem.name}
                            </span>
                            {narItem.time && (
                              <span className="text-[var(--text-tertiary)]">
                                ({narItem.time})
                              </span>
                            )}
                          </div>
                          {narItem.summary && (
                            <p className="text-[var(--text-tertiary)] mt-1 line-clamp-1">
                              {narItem.summary}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Execution type indicator */}
          {executionData && (
            <div className="flex items-center gap-2 text-xs py-2 px-3 rounded-xl bg-[var(--bg-sunken)] border border-[var(--border-subtle)] font-mono">
              {executionData.icon && (
                <span className="text-base">{executionData.icon}</span>
              )}
              <span className="text-[var(--text-primary)] font-medium">
                {executionData.text}
              </span>
              {executionData.desc && (
                <span className="text-[var(--text-tertiary)]">
                  - {executionData.desc}
                </span>
              )}
            </div>
          )}

          {/* Fallback substeps */}
          {step.substeps.length > 0 && !displayData?.items && (
            <div className="space-y-1.5 font-mono">
              {step.substeps.map((substep, i) => (
                <div
                  key={i}
                  className="text-xs text-[var(--text-secondary)] flex items-center gap-2"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)]" />
                  {substep}
                </div>
              ))}
            </div>
          )}

          {/* Selection reason (Step 1 - Narrative Selection) */}
          {selectionReason && (
            <ReasoningBlock
              title={`Selection: ${selectionMethod || 'unknown'} | Retrieval: ${retrievalMethod || 'unknown'}`}
              reason={selectionReason}
              icon={FileText}
            />
          )}

          {/* Decision reasoning (Step 2 - Module Loading) */}
          {decisionReasoning && (
            <ReasoningBlock
              title="LLM Decision Reasoning"
              reason={decisionReasoning}
              icon={Brain}
            />
          )}

          {/* Changes summary */}
          {changesSummary && (
            <ChangesSummary changes={changesSummary} />
          )}

          {/* Relationship graph */}
          {relationshipGraph && (
            <RelationshipGraph graph={relationshipGraph} />
          )}
        </div>
      )}
    </div>
  );
}
