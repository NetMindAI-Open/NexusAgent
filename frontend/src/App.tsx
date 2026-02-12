/**
 * Main App component with routing
 * Route-level code splitting: LoginPage and MainLayout use React.lazy for on-demand loading
 */

import { useState, useEffect, lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useTheme, useTimezoneSync } from '@/hooks';
import { useConfigStore } from '@/stores';
import { api } from '@/lib/api';

const MainLayout = lazy(() => import('@/components/layout/MainLayout'));
const LoginPage = lazy(() => import('@/pages/LoginPage'));

/** Full-screen loading placeholder */
function PageFallback() {
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[var(--bg-deep)]">
      <div className="w-8 h-8 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn, userId, logout } = useConfigStore();
  const [validating, setValidating] = useState(true);

  useEffect(() => {
    if (!isLoggedIn || !userId) {
      setValidating(false);
      return;
    }
    // Validate that the user still exists in the backend DB
    api.login(userId)
      .then(res => {
        if (!res.success) logout();
      })
      .catch(() => {
        // Backend unreachable — don't force logout
      })
      .finally(() => setValidating(false));
  }, [isLoggedIn, userId]);

  if (!isLoggedIn) return <Navigate to="/login" replace />;
  if (validating) return <PageFallback />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useConfigStore();
  if (isLoggedIn) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  const { effectiveTheme } = useTheme();
  useTimezoneSync();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', effectiveTheme === 'dark');
  }, [effectiveTheme]);

  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route
          path="/login"
          element={<PublicRoute><LoginPage /></PublicRoute>}
        />
        <Route
          path="/"
          element={<ProtectedRoute><MainLayout /></ProtectedRoute>}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
