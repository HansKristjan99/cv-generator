import { useAuth } from "@clerk/react";
import { Navigate } from "react-router";

import { LoadingPage } from "../components/loadingPage";

export function AuthRedirect() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return <LoadingPage />;
  }

  return <Navigate to={isSignedIn ? "/app" : "/"} replace />;
}
