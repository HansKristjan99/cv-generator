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
} from "../api/billing/billing";
import { cx } from "../utils/cx";
import styles from "./subscriptionPage.module.css";

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined;
const stripePromise = stripePublishableKey ? loadStripe(stripePublishableKey) : null;

// Optional human-readable price (e.g. "$12 / month"). Stripe owns the real
// amount; when unset we point the user to the secure checkout instead.
const proPriceLabel = import.meta.env.VITE_STRIPE_PRICE_LABEL as string | undefined;

const FREE_FEATURES = [
  "3 CV generations per month",
  "15 refinements per conversation",
  "6 AI suggestions per month",
];

const PRO_FEATURES = [
  "Unlimited CV generations every month",
  "Unlimited refinements in every conversation",
  "Unlimited AI suggestions to fill in the gaps",
];

type LoadState = "loading" | "ready" | "error";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M5 10.5l3.2 3.2L15 7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

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
  const isCheckoutOpen = Boolean(clientSecret && stripePromise);
  const renewalDate = formatDate(subscription?.current_period_end ?? null);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Workspace</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbActive}>Subscription</span>
          </div>
          <h1 className={styles.title}>Subscription</h1>
          <p className={styles.subtitle}>
            Upgrade to Pro for unlimited CV generation, refinements, and AI suggestions.
          </p>
        </div>
        {loadState === "ready" ? (
          isActive ? (
            <span className={styles.statusActive}>
              <span className={styles.statusDot} />
              Pro · Active
            </span>
          ) : (
            <span className={styles.statusFree}>Free plan</span>
          )
        ) : null}
      </header>

      {error ? <p className={cx(styles.banner, styles.bannerError)}>{error}</p> : null}
      {message ? <p className={cx(styles.banner, styles.bannerInfo)}>{message}</p> : null}

      {loadState === "loading" ? (
        <section className={styles.loadingPanel}>Loading your subscription…</section>
      ) : isCheckoutOpen ? (
        <section className={styles.checkout}>
          <div className={styles.checkoutHead}>
            <h2 className={styles.checkoutTitle}>Complete your subscription</h2>
            <button type="button" className={styles.backButton} onClick={cancelCheckout}>
              Back
            </button>
          </div>
          <div className={styles.checkoutBody}>
            <EmbeddedCheckoutProvider
              key={checkoutSessionId ?? clientSecret}
              stripe={stripePromise}
              options={checkoutOptions}
            >
              <EmbeddedCheckout />
            </EmbeddedCheckoutProvider>
          </div>
        </section>
      ) : (
        <div className={styles.grid}>
          <article className={styles.plan}>
            <div className={styles.planHead}>
              <div className={styles.planTopRow}>
                <h2 className={styles.planName}>Free</h2>
                {!isActive ? <span className={styles.planBadgeNeutral}>Current plan</span> : null}
              </div>
              <div className={styles.priceRow}>
                <span className={styles.price}>Free</span>
                <span className={styles.priceUnit}>forever</span>
              </div>
              <p className={styles.planDesc}>Everything you need to try Hireable and ship a polished CV.</p>
            </div>
            <ul className={styles.features}>
              {FREE_FEATURES.map((feature) => (
                <li key={feature} className={styles.feature}>
                  <CheckIcon className={cx(styles.featureIcon, styles.featureIconMuted)} />
                  {feature}
                </li>
              ))}
            </ul>
            <div className={styles.planFoot}>
              {!isActive ? <span className={styles.currentTag}>Your current plan</span> : null}
            </div>
          </article>

          <article className={cx(styles.plan, styles.planFeatured)}>
            <div className={styles.planHead}>
              <div className={styles.planTopRow}>
                <h2 className={styles.planName}>Pro</h2>
                {isActive ? (
                  <span className={styles.planBadge}>Current plan</span>
                ) : (
                  <span className={styles.planBadge}>Recommended</span>
                )}
              </div>
              {proPriceLabel ? (
                <div className={styles.priceRow}>
                  <span className={styles.price}>{proPriceLabel}</span>
                </div>
              ) : (
                <p className={styles.planDesc}>Pricing shown securely at checkout.</p>
              )}
              <p className={styles.planDesc}>Remove every limit and generate as much as your job hunt needs.</p>
            </div>
            <ul className={styles.features}>
              {PRO_FEATURES.map((feature) => (
                <li key={feature} className={styles.feature}>
                  <CheckIcon className={styles.featureIcon} />
                  {feature}
                </li>
              ))}
            </ul>
            <div className={styles.planFoot}>
              {isActive ? (
                <>
                  <button
                    type="button"
                    className={styles.planButtonSecondary}
                    disabled={isOpeningPortal}
                    onClick={openPortal}
                  >
                    {isOpeningPortal ? "Opening…" : "Manage billing"}
                  </button>
                  {renewalDate ? (
                    <p className={styles.renewal}>Renews on {renewalDate}</p>
                  ) : null}
                </>
              ) : (
                <button
                  type="button"
                  className={styles.planButton}
                  disabled={isStartingCheckout || loadState !== "ready"}
                  onClick={startCheckout}
                >
                  {isStartingCheckout ? "Starting…" : "Subscribe to Pro"}
                </button>
              )}
            </div>
          </article>
        </div>
      )}
    </main>
  );
}
