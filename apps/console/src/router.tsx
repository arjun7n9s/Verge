import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppShell from '@/components/templates/AppShell';

// Lazy load route pages
const FindingsView = lazy(() => import('@/pages/FindingsView'));
const AdminView = lazy(() => import('@/pages/AdminView'));
const AuditView = lazy(() => import('@/pages/AuditView'));
const ReplayView = lazy(() => import('@/pages/ReplayView'));
const FleetView = lazy(() => import('@/pages/FleetView'));
const ShiftHandoverView = lazy(() => import('@/pages/ShiftHandoverView'));

function PageFallback() {
  return (
    <div className="flex items-center justify-center h-full w-full bg-bg">
      <div className="flex flex-col items-center gap-3">
        <div className="h-5 w-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-ink-dim font-mono">LOADING VIEW</span>
      </div>
    </div>
  );
}

import { RoleGuard } from '@/components/atoms/RoleGuard';

export default function AppRouter() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<FindingsView />} />
          <Route
            path="/admin"
            element={
              <RoleGuard allowedRoles={['Safety_Engineer', 'administrator']}>
                <AdminView />
              </RoleGuard>
            }
          />
          <Route
            path="/audit"
            element={
              <RoleGuard allowedRoles={['Safety_Engineer', 'administrator']}>
                <AuditView />
              </RoleGuard>
            }
          />
          <Route path="/replay" element={<ReplayView />} />
          <Route path="/fleet" element={<FleetView />} />
          <Route
            path="/handover"
            element={
              <RoleGuard allowedRoles={['Safety_Engineer', 'administrator']}>
                <ShiftHandoverView />
              </RoleGuard>
            }
          />
          {/* Fallback redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
