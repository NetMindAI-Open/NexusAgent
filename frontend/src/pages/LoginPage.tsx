/**
 * Login Page - Bioluminescent Terminal style
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowRight, Sparkles, UserPlus, Zap } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import { useConfigStore } from '@/stores';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { ParticleBackground } from './ParticleBackground';
import { CreateUserDialog } from './CreateUserDialog';

export function LoginPage() {
  const [userId, setUserId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const navigate = useNavigate();
  const { login, setAgents, setAgentId } = useConfigStore();

  const handleLogin = async () => {
    if (!userId.trim()) {
      setError('Please enter your User ID');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const loginRes = await api.login(userId.trim());
      if (!loginRes.success) {
        setError(loginRes.error || 'Login failed');
        setLoading(false);
        return;
      }

      const agentsRes = await api.getAgents(userId.trim());
      if (agentsRes.success && agentsRes.agents.length > 0) {
        setAgents(agentsRes.agents);
        setAgentId(agentsRes.agents[0].agent_id);
      }

      login(userId.trim());
      navigate('/');
    } catch (err) {
      setError('Connection failed. Please try again.');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleLogin();
  };

  return (
    <div className="login-container">
      <ParticleBackground />

      {/* Main login card */}
      <div className="login-card animate-scale-in">
        {/* Logo / Header */}
        <div className="text-center mb-10">
          <div className="relative inline-block mb-5">
            <div className="absolute -inset-4 bg-[var(--accent-primary)] rounded-3xl opacity-20 blur-2xl animate-breathe" />
            <div className="relative w-20 h-20 rounded-2xl bg-[var(--gradient-primary)] flex items-center justify-center shadow-[0_0_40px_var(--accent-glow)] animate-float">
              <Zap className="w-10 h-10 text-[var(--text-inverse)] dark:text-[var(--bg-deep)]" />
            </div>
            <div className="absolute -inset-6 animate-rotate-slow">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-[var(--accent-primary)] shadow-[0_0_10px_var(--accent-primary)]" />
            </div>
          </div>

          <h1 className="text-3xl font-bold font-[family-name:var(--font-display)] text-[var(--text-primary)] mb-2 tracking-tight">
            Nexus<span className="text-[var(--accent-primary)]">Mind</span>
          </h1>
          <p className="text-[var(--text-secondary)] text-sm">Intelligent Agent Platform</p>
          <p className="text-[10px] text-[var(--text-tertiary)] font-mono tracking-[0.2em] uppercase mt-1">
            Enter credentials to continue
          </p>
        </div>

        {/* Login Form */}
        <div className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              User ID
            </label>
            <Input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="your_username"
              disabled={loading}
              error={!!error}
              className={cn('h-12 text-base font-mono', 'bg-[var(--bg-sunken)]')}
              autoFocus
            />
            {error && (
              <p className="text-xs text-[var(--color-error)] animate-slide-up flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-[var(--color-error)]" />
                {error}
              </p>
            )}
          </div>

          <Button
            variant="accent"
            onClick={handleLogin}
            disabled={loading || !userId.trim()}
            className="w-full h-12 text-base font-semibold group"
            glow={!loading && !!userId.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <span>Access Terminal</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </Button>

          {/* Divider */}
          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--border-subtle)]" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 bg-[var(--glass-bg)] text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider">
                or
              </span>
            </div>
          </div>

          {/* Create User Button */}
          <Button
            variant="outline"
            onClick={() => setShowCreateDialog(true)}
            className="w-full h-11 text-sm"
          >
            <UserPlus className="w-4 h-4" />
            <span>Create New User</span>
          </Button>
        </div>

        {/* Footer */}
        <div className="mt-10 pt-6 border-t border-[var(--border-subtle)]">
          <div className="flex items-center justify-center gap-2 text-xs text-[var(--text-tertiary)]">
            <Sparkles className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
            <span>Powered by NexusMind</span>
          </div>
        </div>
      </div>

      {/* Create User Dialog */}
      {showCreateDialog && (
        <CreateUserDialog
          onClose={() => setShowCreateDialog(false)}
          onCreated={(id) => setUserId(id)}
        />
      )}
    </div>
  );
}

export default LoginPage;
