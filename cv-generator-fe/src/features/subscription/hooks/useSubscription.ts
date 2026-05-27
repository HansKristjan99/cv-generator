import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import {
  createBillingPortalSession,
  createCheckoutSession,
  getCheckoutSessionStatus,
  getSubscription,
  type SubscriptionState,
} from "../../../api/billing/billing";
import { stripePromise } from "../lib/stripe";

export type LoadState = "loading" | "ready" | "error";

export type SubscriptionStore = {
  loadState: LoadState;
  subscription: SubscriptionState | null;
  clientSecret: string | null;
  checkoutSessionId: string | null;
  message: string | null;
  error: string | null;
  isStartingCheckout: boolean;
  isOpeningPortal: boolean;
  startCheckout: () => Promise<void>;
  cancelCheckout: () => void;
  openPortal: () => Promise<void>;
  refreshSubscription: () => Promise<SubscriptionState>;
  onCheckoutComplete: () => void;
};

export function useSubscription(): SubscriptionStore {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [subscription, setSubscription] = useState<SubscriptionState | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [checkoutSessionId, setCheckoutSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStartingCheckout, setIsStartingCheckout] = useState(false);
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);

  const refreshSubscription = useCallback(async () => {
    const next = await getSubscription();
    setSubscription(next);
    return next;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    setError(null);
    void refreshSubscription()
      .then(() => {
        if (!cancelled) setLoadState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unable to load subscription.");
        setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshSubscription]);

  useEffect(() => {
    const returnedSessionId = searchParams.get("checkout_session_id");
    if (!returnedSessionId) return;

    let cancelled = false;
    setMessage("Checking your payment status...");
    void getCheckoutSessionStatus(returnedSessionId)
      .then(async (status) => {
        if (cancelled) return;
        await refreshSubscription();
        setMessage(
          status.status === "complete"
            ? "Payment complete. Your subscription will appear here as soon as Stripe confirms it."
            : "Checkout was not completed.",
        );
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete("checkout_session_id");
        setSearchParams(nextParams, { replace: true });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unable to verify checkout status.");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshSubscription, searchParams, setSearchParams]);

  const startCheckout = async () => {
    if (!stripePromise) {
      setError("Stripe publishable key is not configured.");
      return;
    }
    setIsStartingCheckout(true);
    setError(null);
    setMessage(null);
    try {
      const session = await createCheckoutSession();
      setClientSecret(session.client_secret);
      setCheckoutSessionId(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start checkout.");
    } finally {
      setIsStartingCheckout(false);
    }
  };

  const cancelCheckout = () => {
    setClientSecret(null);
    setCheckoutSessionId(null);
  };

  const openPortal = async () => {
    setIsOpeningPortal(true);
    setError(null);
    try {
      const session = await createBillingPortalSession();
      window.location.assign(session.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open billing portal.");
      setIsOpeningPortal(false);
    }
  };

  const onCheckoutComplete = () => {
    setClientSecret(null);
    setCheckoutSessionId(null);
    setMessage("Payment complete. Refreshing your subscription...");
    void refreshSubscription();
  };

  return {
    loadState,
    subscription,
    clientSecret,
    checkoutSessionId,
    message,
    error,
    isStartingCheckout,
    isOpeningPortal,
    startCheckout,
    cancelCheckout,
    openPortal,
    refreshSubscription,
    onCheckoutComplete,
  };
}
