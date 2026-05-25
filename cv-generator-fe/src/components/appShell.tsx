import { type ReactNode, useEffect, useRef, useState } from "react";
import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";
import { useSearchParams } from "react-router";
import { ConversationPage } from "../pages/conversationPage";
import { CvGeneratorPage } from "../pages/cvGeneratorPage";
import { TemplatesPage } from "../pages/templatesPage";
import { UserMemoryPage } from "../pages/userMemoryPage";
import { useAppSelector } from "../hooks";
import { AuthenticatedApiProvider } from "../routes/authenticatedApiProvider";
import { RecentChats } from "./recentChats";
import { cx } from "../utils/cx";
import styles from "./appShell.module.css";
import { SubscriptionPage } from "../pages/subscriptionPage";

type AppTab = "cv" | "templates" | "user memory" | "session" | "subscription";

const tabs: Array<{ id: AppTab; label: string }> = [
  { id: "cv", label: "New CV" },
  { id: "templates", label: "Templates" },
  { id: "user memory", label: "Memory" },
  { id: "subscription", label: "Subscription" },
];

function isAppTab(value: string | null): value is AppTab {
  return (
    value === "cv"
    || value === "templates"
    || value === "user memory"
    || value === "session"
    || value === "subscription"
  );
}

export function AppShell({ initialTab = "cv" }: { initialTab?: AppTab }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<AppTab>(
    isAppTab(tabParam) ? tabParam : initialTab,
  );
  const { isLoaded, isSignedIn } = useAuth();
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);
  const setupStatus = useAppSelector((s) => s.cvGeneration.setupStatus);
  const prevSetupStatus = useRef(setupStatus);

  useEffect(() => {
    if (prevSetupStatus.current === "loading" && setupStatus === "idle" && activeSessionId) {
      setActiveTab("session");
    }
    prevSetupStatus.current = setupStatus;
  }, [setupStatus, activeSessionId]);

  const handleTabClick = (tabId: AppTab) => {
    setActiveTab(tabId);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", tabId);
    nextParams.delete("checkout_session_id");
    setSearchParams(nextParams);
  };

  const showConversation = isSignedIn && activeTab === "session" && Boolean(activeSessionId);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Workspace navigation">
        <div className={styles.brand}>
          <div className={styles.brandTile}>H</div>
          <div>
            <p className={styles.brandName}>Hireable</p>
            <p className={styles.brandTag}>Fine tune your CV</p>
          </div>
        </div>

        <nav className={styles.tabs} aria-label="Workspace tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={cx(styles.tab, isActive && styles.tabActive)}
                aria-current={isActive ? "page" : undefined}
                onClick={() => handleTabClick(tab.id)}
              >
                <span className={styles.tabText}>
                  <span className={styles.tabLabel}>{tab.label}</span>
                </span>
                {isActive ? <span className={styles.tabDot} /> : null}
              </button>
            );
          })}
        </nav>

        {isSignedIn && (
          <div className={styles.recentChats}>
            <RecentChats onOpenSession={() => setActiveTab("session")} />
          </div>
        )}

        <div className={styles.footerArea}>
          <div className={styles.account}>
            {!isLoaded ? (
              <p className={styles.status}>Loading…</p>
            ) : isSignedIn ? (
              <UserButton />
            ) : (
              <div className={styles.authBox}>
                <SignInButton mode="modal">
                  <button type="button" className={styles.authButton}>
                    Sign in
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button type="button" className={styles.authButtonSecondary}>
                    Create account
                  </button>
                </SignUpButton>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className={styles.main}>
        {isLoaded && isSignedIn ? (
          <AuthenticatedApiProvider>
            {showConversation ? <ConversationPage /> : renderAuthenticatedTab(activeTab)}
          </AuthenticatedApiProvider>
        ) : (
          renderTab(activeTab, isLoaded, isSignedIn)
        )}
      </main>
    </div>
  );
}

function renderAuthenticatedTab(activeTab: AppTab) {
  if (activeTab === "templates") {
    return <TemplatesPage />;
  }

  if (activeTab === "user memory") {
    return <UserMemoryPage />;
  }

  if (activeTab === "subscription") {
    return <SubscriptionPage />;
  }

  return <CvGeneratorPage />;
}

function renderTab(activeTab: AppTab, isLoaded: boolean, isSignedIn: boolean | undefined) {
  if (activeTab === "templates") {
    return (
      <AuthenticatedTab title="Templates" isLoaded={isLoaded} isSignedIn={isSignedIn}>
        <TemplatesPage />
      </AuthenticatedTab>
    );
  }

  if (activeTab === "user memory") {
    return (
      <AuthenticatedTab title="Memory" isLoaded={isLoaded} isSignedIn={isSignedIn}>
        <UserMemoryPage />
      </AuthenticatedTab>
    );
  }

  if (activeTab === "subscription") {
    return (
      <AuthenticatedTab title="Subscription" isLoaded={isLoaded} isSignedIn={isSignedIn}>
        <SubscriptionPage />
      </AuthenticatedTab>
    );
  }

  return (
    <AuthenticatedTab title="New CV" isLoaded={isLoaded} isSignedIn={isSignedIn}>
      <CvGeneratorPage />
    </AuthenticatedTab>
  );
}

function AuthenticatedTab({
  title,
  isLoaded,
  isSignedIn,
  children,
}: {
  title: string;
  isLoaded: boolean;
  isSignedIn: boolean | undefined;
  children: ReactNode;
}) {
  if (!isLoaded) {
    return <Placeholder title="Loading…" compact />;
  }

  if (!isSignedIn) {
    return (
      <section className={styles.placeholder}>
        <p className={styles.placeholderEyebrow}>{title}</p>
        <h2 className={styles.placeholderTitle}>Sign in to continue</h2>
        <div className={styles.signInActions}>
          <SignInButton mode="modal">
            <button type="button" className={styles.authButton}>
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className={styles.authButtonSecondary}>
              Create account
            </button>
          </SignUpButton>
        </div>
      </section>
    );
  }

  return children;
}

function Placeholder({ title, compact = false }: { title: string; compact?: boolean }) {
  return (
    <section className={cx(styles.placeholder, compact && styles.placeholderCompact)}>
      <p className={styles.placeholderEyebrow}>{title}</p>
      <h2 className={styles.placeholderTitle}>{compact ? title : "Coming soon"}</h2>
    </section>
  );
}
