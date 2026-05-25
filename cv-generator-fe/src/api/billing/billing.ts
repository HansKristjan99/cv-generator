import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type SubscriptionState = {
  subscription_type: string | null;
  active: boolean;
  status: string | null;
  current_period_end: string | null;
};

export type CreateCheckoutSessionResponse = {
  client_secret: string;
  session_id: string;
};

export type CheckoutSessionStatus = {
  status: string | null;
  payment_status: string | null;
};

export type BillingPortalSession = {
  url: string;
};

export async function getSubscription(): Promise<SubscriptionState> {
  const response = await authFetch("/billing/subscription/");
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return (await response.json()) as SubscriptionState;
}

export async function createCheckoutSession(): Promise<CreateCheckoutSessionResponse> {
  const response = await authFetch("/billing/checkout_session/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as CreateCheckoutSessionResponse;
}

export async function getCheckoutSessionStatus(sessionId: string): Promise<CheckoutSessionStatus> {
  const response = await authFetch(`/billing/checkout_session/${sessionId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return (await response.json()) as CheckoutSessionStatus;
}

export async function createBillingPortalSession(): Promise<BillingPortalSession> {
  const response = await authFetch("/billing/portal_session/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as BillingPortalSession;
}
