import { useEffect, useState, type ReactNode } from 'react';
import { keycloak, keycloakEnabled } from '@/lib/keycloak';
import { useAuthStore } from '@/stores/auth';

interface AuthProviderProps {
  children: ReactNode;
}

function rolesFromToken(): string[] {
  if (!keycloak?.tokenParsed) return [];
  const parsed = keycloak.tokenParsed as Record<string, unknown>;
  const realmRoles = (parsed.realm_access as { roles?: string[] } | undefined)?.roles ?? [];
  const clientRoles =
    (parsed.resource_access as Record<string, { roles?: string[] }> | undefined)?.[
      keycloak.clientId ?? 'verge-console'
    ]?.roles ?? [];
  return [...new Set([...realmRoles, ...clientRoles])];
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { setUser, clearUser } = useAuthStore();
  const [ready, setReady] = useState(!keycloakEnabled);

  useEffect(() => {
    if (!keycloakEnabled || !keycloak) {
      return;
    }

    const kc = keycloak;
    let cancelled = false;
    kc.init({ onLoad: 'login-required', checkLoginIframe: false })
      .then((authenticated) => {
        if (cancelled || !authenticated || !kc.tokenParsed) {
          return;
        }
        const parsed = kc.tokenParsed as Record<string, unknown>;
        setUser({
          id: String(parsed.sub ?? 'unknown'),
          name: String(parsed.name ?? parsed.preferred_username ?? 'Operator'),
          email: String(parsed.email ?? ''),
          roles: rolesFromToken(),
        });
        setReady(true);
      })
      .catch(() => {
        clearUser();
        setReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, [setUser, clearUser]);

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-screen w-full bg-bg font-mono text-xs">
        <span className="animate-pulse text-ink-dim">AUTHENTICATING SESSION...</span>
      </div>
    );
  }

  return <>{children}</>;
}

export function getAuthHeaders(): Record<string, string> {
  if (keycloakEnabled && keycloak?.token) {
    return { Authorization: `Bearer ${keycloak.token}` };
  }
  return {};
}
