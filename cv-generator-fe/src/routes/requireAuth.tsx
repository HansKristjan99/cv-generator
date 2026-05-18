import type { ReactNode } from "react";
import { useAuth } from "@clerk/react";
import { Navigate } from "react-router";

import { LoadingPage } from "../components/loadingPage";
import { AuthenticatedApiProvider } from "./authenticatedApiProvider";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth();
  console.log("RequireAuth state:", { isLoaded, isSignedIn });

  if (!isLoaded) {
    return <LoadingPage />;
  }

  if (!isSignedIn) {
    return <Navigate to="/" replace />;
  }

  return <AuthenticatedApiProvider>{children}</AuthenticatedApiProvider>;
}
