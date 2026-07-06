import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth';
import { ShieldAlert } from 'lucide-react';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: string[];
}

export function RoleGuard({ children, allowedRoles }: RoleGuardProps) {
  const { user, isAuthenticated, setUser } = useAuthStore();

  // Auto-seed a default Safety Engineer profile for local dev only.
  useEffect(() => {
    if (import.meta.env.DEV && !isAuthenticated) {
      setUser({
        id: 'user-0411',
        name: 'Shift Supervisor Sarah',
        email: 'sarah@verge.internal',
        roles: ['Safety_Engineer'],
      });
    }
  }, [isAuthenticated, setUser]);

  if (!isAuthenticated || !user) {
    return (
      <div className="flex items-center justify-center h-full w-full bg-bg font-mono text-xs">
        <span className="animate-pulse text-ink-dim">AUTHENTICATING SESSION...</span>
      </div>
    );
  }

  const hasRole = user.roles.some((r) => allowedRoles.includes(r));

  if (!hasRole) {
    return (
      <div className="flex flex-col items-center justify-center h-full w-full p-6 text-center select-none text-ink">
        <div className="bg-imminent/10 border border-imminent/20 p-6 rounded-md max-w-sm flex flex-col items-center gap-3">
          <ShieldAlert className="h-10 w-10 text-imminent animate-bounce" />
          <h2 className="text-base font-bold uppercase font-mono text-imminent tracking-wide">
            403 - FORBIDDEN
          </h2>
          <p className="text-xs text-ink-dim leading-relaxed font-mono">
            Role authentication failed. This console workspace is restricted to Safety Engineers and administrators only.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
