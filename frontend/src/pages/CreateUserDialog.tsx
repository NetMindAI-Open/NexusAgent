/**
 * Create User Dialog - admin creates a new user
 */

import { useState } from 'react';
import { Loader2, UserPlus, X, Check } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import { api } from '@/lib/api';

interface CreateUserDialogProps {
  onClose: () => void;
  onCreated: (userId: string) => void;
}

export function CreateUserDialog({ onClose, onCreated }: CreateUserDialogProps) {
  const [userId, setUserId] = useState('');
  const [adminSecretKey, setAdminSecretKey] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleCreate = async () => {
    if (!userId.trim()) {
      setError('Please enter a User ID');
      return;
    }
    if (!adminSecretKey.trim()) {
      setError('Please enter the Admin Secret Key');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);

    try {
      const res = await api.createUser(
        userId.trim(),
        adminSecretKey.trim(),
        displayName.trim() || undefined
      );

      if (res.success) {
        setSuccess(true);
        onCreated(userId.trim());
        setTimeout(onClose, 1500);
      } else {
        setError(res.error || 'Failed to create user');
      }
    } catch {
      setError('Connection failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[var(--bg-deep)]/80 backdrop-blur-md"
        onClick={() => !loading && onClose()}
      />

      {/* Dialog */}
      <div className="relative bg-[var(--glass-bg)] backdrop-blur-xl border border-[var(--glass-border)] rounded-3xl shadow-[var(--shadow-lg),0_0_60px_var(--accent-glow)] w-full max-w-md p-7 animate-scale-in">
        {/* Top glow line */}
        <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent" />

        {/* Close Button */}
        <button
          onClick={() => !loading && onClose()}
          className="absolute top-4 right-4 p-2 rounded-xl hover:bg-[var(--bg-secondary)] transition-colors"
          disabled={loading}
        >
          <X className="w-5 h-5 text-[var(--text-tertiary)]" />
        </button>

        {/* Header */}
        <div className="text-center mb-7">
          <div className="relative inline-block mb-4">
            <div className="w-14 h-14 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center shadow-[0_0_30px_var(--accent-glow)]">
              <UserPlus className="w-7 h-7 text-[var(--text-inverse)] dark:text-[var(--bg-deep)]" />
            </div>
            <div className="absolute -inset-2 bg-[var(--accent-primary)] rounded-2xl opacity-20 blur-xl -z-10" />
          </div>
          <h2 className="text-xl font-bold font-[family-name:var(--font-display)] text-[var(--text-primary)]">
            Create New User
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Admin authorization required
          </p>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-5 p-4 bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 rounded-xl flex items-center gap-3 animate-slide-up">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-success)]/20 flex items-center justify-center">
              <Check className="w-5 h-5 text-[var(--color-success)]" />
            </div>
            <span className="text-[var(--color-success)] text-sm font-medium">
              User created successfully!
            </span>
          </div>
        )}

        {/* Form */}
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              User ID <span className="text-[var(--color-error)]">*</span>
            </label>
            <Input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="your_username"
              disabled={loading || success}
              className="h-11 font-mono"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Display Name
            </label>
            <Input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional display name"
              disabled={loading || success}
              className="h-11"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Admin Secret Key <span className="text-[var(--color-error)]">*</span>
            </label>
            <Input
              type="password"
              value={adminSecretKey}
              onChange={(e) => setAdminSecretKey(e.target.value)}
              placeholder="Enter admin secret key"
              disabled={loading || success}
              className="h-11 font-mono"
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--color-error)] animate-slide-up flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-[var(--color-error)]" />
              {error}
            </p>
          )}

          <Button
            variant="accent"
            onClick={handleCreate}
            disabled={loading || success || !userId.trim() || !adminSecretKey.trim()}
            className="w-full h-11 font-semibold mt-2"
            glow={!loading && !success && !!userId.trim() && !!adminSecretKey.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Creating...</span>
              </>
            ) : success ? (
              <>
                <Check className="w-4 h-4" />
                <span>Created!</span>
              </>
            ) : (
              <span>Create User</span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
