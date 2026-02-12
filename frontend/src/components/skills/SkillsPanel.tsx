/**
 * @file_name: SkillsPanel.tsx
 * @author: Bin Liang
 * @date: 2026-02-03
 * @description: Skills management panel
 *
 * Features:
 * - Display user's installed Skills
 * - Support installing Skills from GitHub or zip files
 * - Support disabling/enabling/removing Skills
 * - Support Study feature: Agent automatically learns Skill documentation
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Puzzle,
  RefreshCw,
  Github,
  FileArchive,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  X,
  Plus,
  BookOpen,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from '@/components/ui';
import { useConfigStore } from '@/stores';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import type { SkillInfo } from '@/types/skills';

// Install mode
type InstallMode = 'github' | 'zip' | null;

// Skill card component
function SkillCard({
  skill,
  onToggle,
  onRemove,
  onStudy,
  isToggling,
  isRemoving,
  isStudying,
}: {
  skill: SkillInfo;
  onToggle: (skill: SkillInfo) => void;
  onRemove: (skill: SkillInfo) => void;
  onStudy: (skill: SkillInfo) => void;
  isToggling: boolean;
  isRemoving: boolean;
  isStudying: boolean;
}) {
  const [showResult, setShowResult] = useState(false);
  const studying = isStudying || skill.study_status === 'studying';

  return (
    <div
      className={cn(
        'p-4 rounded-xl transition-all duration-300',
        'border bg-[var(--bg-elevated)]',
        skill.disabled
          ? 'border-[var(--border-subtle)] opacity-60'
          : 'border-[var(--border-subtle)] hover:border-[var(--accent-primary)]/20 hover:shadow-lg'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 bg-[var(--accent-secondary)]/10">
          <Puzzle className="w-5 h-5 text-[var(--accent-secondary)]" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span
              className={cn(
                'text-sm font-semibold truncate',
                skill.disabled
                  ? 'text-[var(--text-tertiary)] line-through'
                  : 'text-[var(--text-primary)]'
              )}
            >
              {skill.name}
            </span>
          </div>

          {skill.description && (
            <p className="text-xs text-[var(--text-tertiary)] line-clamp-2 mb-2">
              {skill.description}
            </p>
          )}

          {skill.version && (
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              v{skill.version}
            </span>
          )}

          {/* Study status display */}
          {studying && (
            <div className="flex items-center gap-2 mt-2 px-2 py-1.5 rounded-lg bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/10">
              <Loader2 className="w-3 h-3 animate-spin text-[var(--accent-primary)]" />
              <span className="text-xs text-[var(--accent-primary)]">Studying...</span>
            </div>
          )}

          {/* Study failed */}
          {skill.study_status === 'failed' && skill.study_error && (
            <div className="flex items-center gap-2 mt-2 px-2 py-1.5 rounded-lg bg-[var(--color-error)]/5 border border-[var(--color-error)]/10">
              <AlertCircle className="w-3 h-3 text-[var(--color-error)]" />
              <span className="text-xs text-[var(--color-error)] truncate">{skill.study_error}</span>
            </div>
          )}

          {/* Study result */}
          {skill.study_status === 'completed' && skill.study_result && (
            <div className="mt-2">
              <button
                onClick={() => setShowResult(!showResult)}
                className="flex items-center gap-1 text-xs text-[var(--accent-secondary)] hover:text-[var(--accent-primary)] transition-colors"
              >
                {showResult ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                <BookOpen className="w-3 h-3" />
                Study Result
              </button>
              {showResult && (
                <div className="mt-1.5 p-2.5 rounded-lg bg-[var(--bg-sunken)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {skill.study_result}
                </div>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--border-subtle)]">
            {/* Study button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onStudy(skill)}
              disabled={studying || skill.disabled}
              className="text-xs text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/10"
            >
              {studying ? (
                <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
              ) : (
                <BookOpen className="w-3 h-3 mr-1.5" />
              )}
              {skill.study_status === 'completed' ? 'Re-study' : 'Study'}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggle(skill)}
              disabled={isToggling}
              className={cn(
                'text-xs',
                skill.disabled
                  ? 'text-[var(--color-success)] hover:bg-[var(--color-success)]/10'
                  : 'text-[var(--color-warning)] hover:bg-[var(--color-warning)]/10'
              )}
            >
              {isToggling ? (
                <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
              ) : skill.disabled ? (
                <ToggleRight className="w-3 h-3 mr-1.5" />
              ) : (
                <ToggleLeft className="w-3 h-3 mr-1.5" />
              )}
              {skill.disabled ? 'Enable' : 'Disable'}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemove(skill)}
              disabled={isRemoving}
              className="text-xs text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
            >
              {isRemoving ? (
                <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
              ) : (
                <Trash2 className="w-3 h-3 mr-1.5" />
              )}
              Remove
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Install dialog component
function InstallDialog({
  mode,
  onClose,
  onInstall,
  isInstalling,
}: {
  mode: InstallMode;
  onClose: () => void;
  onInstall: (data: { url?: string; branch?: string; file?: File }) => void;
  isInstalling: boolean;
}) {
  const [url, setUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'github') {
      if (!url.trim()) {
        setError('GitHub URL is required');
        return;
      }
      onInstall({ url: url.trim(), branch: branch.trim() || 'main' });
    } else if (mode === 'zip') {
      if (!file) {
        setError('Please select a zip file');
        return;
      }
      onInstall({ file });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.zip')) {
        setError('Please select a .zip file');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  if (!mode) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
            {mode === 'github' ? (
              <>
                <Github className="w-5 h-5" />
                Install from GitHub
              </>
            ) : (
              <>
                <FileArchive className="w-5 h-5" />
                Install from Zip
              </>
            )}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
          >
            <X className="w-4 h-4 text-[var(--text-tertiary)]" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* GitHub URL */}
          {mode === 'github' && (
            <>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
                  GitHub URL
                </label>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://github.com/username/skill-repo"
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-sunken)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
                  Branch (optional)
                </label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-sunken)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
                />
              </div>
            </>
          )}

          {/* Zip file upload */}
          {mode === 'zip' && (
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
                Skill Package (.zip)
              </label>
              <div
                className={cn(
                  'relative border-2 border-dashed rounded-xl p-6 transition-colors cursor-pointer',
                  file
                    ? 'border-[var(--color-success)] bg-[var(--color-success)]/5'
                    : 'border-[var(--border-subtle)] hover:border-[var(--accent-primary)]/50'
                )}
              >
                <input
                  type="file"
                  accept=".zip"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="flex flex-col items-center justify-center gap-2 text-center">
                  {file ? (
                    <>
                      <CheckCircle className="w-8 h-8 text-[var(--color-success)]" />
                      <span className="text-sm text-[var(--text-primary)]">{file.name}</span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                    </>
                  ) : (
                    <>
                      <FileArchive className="w-8 h-8 text-[var(--text-tertiary)]" />
                      <span className="text-sm text-[var(--text-secondary)]">
                        Click or drag to upload
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        .zip files only
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-error)]/10 border border-[var(--color-error)]/20">
              <AlertCircle className="w-4 h-4 text-[var(--color-error)]" />
              <span className="text-xs text-[var(--color-error)]">{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isInstalling}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="default"
              disabled={isInstalling}
              className="flex-1"
            >
              {isInstalling ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Installing...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Install
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function SkillsPanel() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [installMode, setInstallMode] = useState<InstallMode>(null);
  const [isInstalling, setIsInstalling] = useState(false);
  const [togglingSkill, setTogglingSkill] = useState<string | null>(null);
  const [removingSkill, setRemovingSkill] = useState<string | null>(null);
  const [studyingSkill, setStudyingSkill] = useState<string | null>(null);
  const [showDisabled, setShowDisabled] = useState(false);

  // Interval ref for polling study status
  const studyPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { agentId, userId } = useConfigStore();

  // Load Skills
  const loadSkills = useCallback(async () => {
    if (!agentId || !userId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.listSkills(agentId, userId, showDisabled);
      setSkills(response.skills);
    } catch (err) {
      console.error('Failed to load skills:', err);
      setError(err instanceof Error ? err.message : 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  }, [agentId, userId, showDisabled]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  // After page load, check if any Skill is being studied and auto-resume polling
  useEffect(() => {
    const studyingSkills = skills.filter((s) => s.study_status === 'studying');
    if (studyingSkills.length > 0 && !studyPollRef.current) {
      setStudyingSkill(studyingSkills[0].name);
      startStudyPolling(studyingSkills[0].name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skills]);

  // Clean up polling on component unmount
  useEffect(() => {
    return () => {
      if (studyPollRef.current) {
        clearInterval(studyPollRef.current);
      }
    };
  }, []);

  // Start study status polling
  const startStudyPolling = (skillName: string) => {
    // Clear existing polling
    if (studyPollRef.current) {
      clearInterval(studyPollRef.current);
    }

    studyPollRef.current = setInterval(async () => {
      if (!agentId || !userId) return;

      try {
        const status = await api.getSkillStudyStatus(skillName, agentId, userId);
        if (status.study_status === 'completed' || status.study_status === 'failed') {
          // Study completed or failed, stop polling, refresh list
          if (studyPollRef.current) {
            clearInterval(studyPollRef.current);
            studyPollRef.current = null;
          }
          setStudyingSkill(null);
          loadSkills();
        }
      } catch (err) {
        console.error('Failed to poll study status:', err);
      }
    }, 3000);
  };

  // Install Skill
  const handleInstall = async (data: {
    url?: string;
    branch?: string;
    file?: File;
  }) => {
    if (!agentId || !userId) return;

    setIsInstalling(true);

    try {
      if (installMode === 'github' && data.url) {
        await api.installSkillFromGithub(
          agentId,
          userId,
          data.url,
          data.branch || 'main'
        );
      } else if (installMode === 'zip' && data.file) {
        await api.installSkillFromZip(agentId, userId, data.file);
      }

      setInstallMode(null);
      loadSkills();
    } catch (err) {
      console.error('Failed to install skill:', err);
      alert(err instanceof Error ? err.message : 'Failed to install skill');
    } finally {
      setIsInstalling(false);
    }
  };

  // Toggle Skill status
  const handleToggle = async (skill: SkillInfo) => {
    if (!agentId || !userId) return;

    setTogglingSkill(skill.name);

    try {
      if (skill.disabled) {
        await api.enableSkill(skill.name, agentId, userId);
      } else {
        await api.disableSkill(skill.name, agentId, userId);
      }
      loadSkills();
    } catch (err) {
      console.error('Failed to toggle skill:', err);
      alert(err instanceof Error ? err.message : 'Failed to toggle skill');
    } finally {
      setTogglingSkill(null);
    }
  };

  // Remove Skill
  const handleRemove = async (skill: SkillInfo) => {
    if (!agentId || !userId) return;

    if (!confirm(`Are you sure you want to remove "${skill.name}"? This action cannot be undone.`)) {
      return;
    }

    setRemovingSkill(skill.name);

    try {
      await api.removeSkill(skill.name, agentId, userId);
      loadSkills();
    } catch (err) {
      console.error('Failed to remove skill:', err);
      alert(err instanceof Error ? err.message : 'Failed to remove skill');
    } finally {
      setRemovingSkill(null);
    }
  };

  // Trigger Skill study
  const handleStudy = async (skill: SkillInfo) => {
    if (!agentId || !userId) return;

    setStudyingSkill(skill.name);

    try {
      const response = await api.studySkill(skill.name, agentId, userId);
      if (response.success) {
        // Start polling
        startStudyPolling(skill.name);
        // Immediately refresh list to show studying status
        loadSkills();
      } else {
        alert(response.message || 'Failed to start study');
        setStudyingSkill(null);
      }
    } catch (err) {
      console.error('Failed to start skill study:', err);
      alert(err instanceof Error ? err.message : 'Failed to start study');
      setStudyingSkill(null);
    }
  };

  return (
    <Card variant="glass" className="flex flex-col h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[var(--accent-secondary)]/10 flex items-center justify-center">
            <Puzzle className="w-4 h-4 text-[var(--accent-secondary)]" />
          </div>
          <span>Skills</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant={skills.length > 0 ? 'accent' : 'default'} className="font-mono">
            {skills.length}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            onClick={loadSkills}
            disabled={loading}
            title="Refresh"
            className="hover:bg-[var(--accent-glow)]"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>

      {/* Action bar */}
      <div className="px-4 pb-3 flex items-center justify-between gap-2">
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setInstallMode('github')}
            className="text-xs"
          >
            <Github className="w-3.5 h-3.5 mr-1.5" />
            From GitHub
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setInstallMode('zip')}
            className="text-xs"
          >
            <FileArchive className="w-3.5 h-3.5 mr-1.5" />
            From Zip
          </Button>
        </div>

        <label className="flex items-center gap-2 text-xs text-[var(--text-tertiary)] cursor-pointer">
          <input
            type="checkbox"
            checked={showDisabled}
            onChange={(e) => setShowDisabled(e.target.checked)}
            className="rounded border-[var(--border-default)]"
          />
          Show disabled
        </label>
      </div>

      <CardContent className="flex-1 overflow-hidden min-h-0">
        {error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-8">
              <div className="w-14 h-14 rounded-2xl bg-[var(--color-error)]/10 mx-auto mb-4 flex items-center justify-center">
                <AlertCircle className="w-7 h-7 text-[var(--color-error)]" />
              </div>
              <p className="text-[var(--color-error)] text-sm font-medium mb-1">Error</p>
              <p className="text-[var(--text-tertiary)] text-xs">{error}</p>
              <Button variant="ghost" size="sm" onClick={loadSkills} className="mt-4">
                <RefreshCw className="w-3 h-3 mr-1.5" />
                Retry
              </Button>
            </div>
          </div>
        ) : loading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          </div>
        ) : skills.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-8">
              <div className="w-14 h-14 rounded-2xl bg-[var(--accent-secondary)]/10 mx-auto mb-4 flex items-center justify-center">
                <Puzzle className="w-7 h-7 text-[var(--accent-secondary)]" />
              </div>
              <p className="text-[var(--text-secondary)] text-sm font-medium mb-1">
                No skills installed
              </p>
              <p className="text-[var(--text-tertiary)] text-xs">
                Install skills from GitHub or upload a zip file
              </p>
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto space-y-2 py-2">
            {skills.map((skill) => (
              <SkillCard
                key={skill.name}
                skill={skill}
                onToggle={handleToggle}
                onRemove={handleRemove}
                onStudy={handleStudy}
                isToggling={togglingSkill === skill.name}
                isRemoving={removingSkill === skill.name}
                isStudying={studyingSkill === skill.name}
              />
            ))}
          </div>
        )}
      </CardContent>

      {/* Install dialog */}
      <InstallDialog
        mode={installMode}
        onClose={() => setInstallMode(null)}
        onInstall={handleInstall}
        isInstalling={isInstalling}
      />
    </Card>
  );
}

export default SkillsPanel;
