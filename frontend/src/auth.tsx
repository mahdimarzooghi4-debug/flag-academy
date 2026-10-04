import type { PropsWithChildren } from "react";
import { AuthProvider } from "react-oidc-context";

const authority = import.meta.env.VITE_OIDC_AUTHORITY ?? "http://localhost:8080/realms/parcham";
const clientId = import.meta.env.VITE_OIDC_CLIENT_ID ?? "parcham-web";
const redirectUri = import.meta.env.VITE_OIDC_REDIRECT_URI ?? window.location.origin;

export function ParchamAuthProvider({ children }: PropsWithChildren) {
  return (
    <AuthProvider
      authority={authority}
      client_id={clientId}
      redirect_uri={redirectUri}
      response_type="code"
      scope="openid profile email"
      automaticSilentRenew
      onSigninCallback={() => {
        window.history.replaceState({}, document.title, window.location.pathname);
      }}
    >
      {children}
    </AuthProvider>
  );
}
