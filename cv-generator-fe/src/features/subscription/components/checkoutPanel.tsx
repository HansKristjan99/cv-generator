import { useMemo } from "react";
import { EmbeddedCheckout, EmbeddedCheckoutProvider } from "@stripe/react-stripe-js";

import { stripePromise } from "../lib/stripe";
import styles from "../subscription.module.css";

type Props = {
  clientSecret: string;
  checkoutSessionId: string | null;
  onCancel: () => void;
  onComplete: () => void;
};

export function CheckoutPanel({ clientSecret, checkoutSessionId, onCancel, onComplete }: Props) {
  const options = useMemo(
    () => ({ clientSecret, onComplete }),
    [clientSecret, onComplete],
  );

  return (
    <section className={styles.checkout}>
      <div className={styles.checkoutHead}>
        <h2 className={styles.checkoutTitle}>Complete your subscription</h2>
        <button type="button" className={styles.backButton} onClick={onCancel}>
          Back
        </button>
      </div>
      <div className={styles.checkoutBody}>
        <EmbeddedCheckoutProvider
          key={checkoutSessionId ?? clientSecret}
          stripe={stripePromise}
          options={options}
        >
          <EmbeddedCheckout />
        </EmbeddedCheckoutProvider>
      </div>
    </section>
  );
}
