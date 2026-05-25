import { useCallback, useEffect, useMemo, useState } from "react";
import { EmbeddedCheckout, EmbeddedCheckoutProvider } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { useSearchParams } from "react-router";

import {
  createBillingPortalSession,
  createCheckoutSession,
  getCheckoutSessionStatus,
  getSubscription,
  type SubscriptionState,
} from "../api/billing/createCheckoutSession";
import styles from "./subscriptionPage.module.css";

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined;
const stripePromise = stripePublishableKey ? loadStripe(stripePublishableKey) : null;

type LoadState = "loading" | "ready" | "error";

export function SubscriptionPage() {
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
        if (status.status === "complete") {
          setMessage("Payment complete. Your subscription will appear here as soon as Stripe confirms it.");
        } else {
          setMessage("Checkout was not completed.");
        }
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

  const checkoutOptions = useMemo(
    () => ({
      clientSecret,
      onComplete: () => {
        setClientSecret(null);
        setCheckoutSessionId(null);
        setMessage("Payment complete. Refreshing your subscription...");
        void refreshSubscription();
      },
    }),
    [clientSecret, refreshSubscription],
  );

  const isActive = Boolean(subscription?.active);
  const planLabel = subscription?.subscription_type === "pro" ? "Pro" : "Free";

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>Billing</p>
        <h1 className={styles.title}>Subscription</h1>
      </div>

      {loadState === "loading" ? <p className={styles.status}>Loading subscription...</p> : null}
      {error ? <p className={styles.error}>{error}</p> : null}
      {message ? <p className={styles.message}>{message}</p> : null}

      <div className={styles.planPanel}>
        <div>
          <p className={styles.planName}>{isActive ? `${planLabel} plan` : "Free plan"}</p>
          <p className={styles.planMeta}>
            {isActive
              ? `Status: ${subscription?.status ?? "active"}`
              : "Upgrade to unlock paid CV generation limits."}
          </p>
        </div>

        {isActive ? (
          <button
            type="button"
            className={styles.primaryButton}
            disabled={isOpeningPortal}
            onClick={openPortal}
          >
            {isOpeningPortal ? "Opening..." : "Manage billing"}
          </button>
        ) : (
          <button
            type="button"
            className={styles.primaryButton}
            disabled={isStartingCheckout || loadState !== "ready"}
            onClick={startCheckout}
          >
            {isStartingCheckout ? "Starting..." : "Subscribe"}
          </button>
        )}
      </div>

      {clientSecret && stripePromise ? (
        <div className={styles.checkoutPanel}>
          <EmbeddedCheckoutProvider
            key={checkoutSessionId ?? clientSecret}
            stripe={stripePromise}
            options={checkoutOptions}
          >
            <EmbeddedCheckout />
          </EmbeddedCheckoutProvider>
        </div>
      ) : null}
    </section>
  );
}
