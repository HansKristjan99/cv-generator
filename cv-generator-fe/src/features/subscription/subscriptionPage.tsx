import { cx } from "../../utils/cx";
import { CheckoutPanel } from "./components/checkoutPanel";
import { FreePlanCard } from "./components/freePlanCard";
import { ProPlanCard } from "./components/proPlanCard";
import { SubscriptionHeader } from "./components/subscriptionHeader";
import { useSubscription } from "./hooks/useSubscription";
import { formatDate } from "./lib/formatDate";
import { stripePromise } from "./lib/stripe";
import styles from "./subscription.module.css";

export function SubscriptionPage() {
  const {
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
    onCheckoutComplete,
  } = useSubscription();

  const isActive = Boolean(subscription?.active);
  const isCheckoutOpen = Boolean(clientSecret && stripePromise);
  const renewalDate = formatDate(subscription?.current_period_end ?? null);

  return (
    <main className={styles.page}>
      <SubscriptionHeader loadState={loadState} isActive={isActive} />

      {error ? <p className={cx(styles.banner, styles.bannerError)}>{error}</p> : null}
      {message ? <p className={cx(styles.banner, styles.bannerInfo)}>{message}</p> : null}

      {loadState === "loading" ? (
        <section className={styles.loadingPanel}>Loading your subscription…</section>
      ) : isCheckoutOpen && clientSecret ? (
        <CheckoutPanel
          clientSecret={clientSecret}
          checkoutSessionId={checkoutSessionId}
          onCancel={cancelCheckout}
          onComplete={onCheckoutComplete}
        />
      ) : (
        <div className={styles.grid}>
          <FreePlanCard isActive={isActive} />
          <ProPlanCard
            isActive={isActive}
            renewalDate={renewalDate}
            isStartingCheckout={isStartingCheckout}
            isOpeningPortal={isOpeningPortal}
            canSubscribe={loadState === "ready"}
            onSubscribe={startCheckout}
            onManageBilling={openPortal}
          />
        </div>
      )}
    </main>
  );
}
