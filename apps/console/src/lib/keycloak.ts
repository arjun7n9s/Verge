import Keycloak from 'keycloak-js';

const url = import.meta.env.VITE_KEYCLOAK_URL as string | undefined;

export const keycloakEnabled = Boolean(url && url.length > 0);

export const keycloak = keycloakEnabled
  ? new Keycloak({
      url: url!.replace(/\/$/, ''),
      realm: (import.meta.env.VITE_KEYCLOAK_REALM as string) || 'verge',
      clientId: (import.meta.env.VITE_KEYCLOAK_CLIENT_ID as string) || 'verge-console',
    })
  : null;
