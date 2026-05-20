import { type ReactNode, useState } from "react";
import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";

import { ConversationPage } from "../pages/conversationPage";
import { CvGeneratorPage } from "../pages/cvGeneratorPage";
import { TemplatesPage } from "../pages/templatesPage";
import { UserMemoryPage } from "../pages/userMemoryPage";
import { resetChat } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { AuthenticatedApiProvider } from "../routes/authenticatedApiProvider";
import { RecentChats } from "./recentChats";
import { cx } from "../utils/cx";
import styles from "./appShell.module.css";

type AppTab = "cv" | "templates" | "user memory";

const tabs: Array<{ id: AppTab; label: string; detail: string }> = [
  { id: "cv", label: "Tailor", detail: "Generator" },
  { id: "templates", label: "Templates", detail: "CV layouts" },
  { id: "user memory", label: "Memory", detail: "Profile data" },
];

export function AppShell({ initialTab = "cv" }: { initialTab?: AppTab }) {
  const [activeTab, setActiveTab] = useState<AppTab>(initialTab);
  const { isLoaded, isSignedIn } = useAuth();
  const dispatch = useAppDispatch();
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);

  const handleTabClick = (tabId: AppTab) => {
    setActiveTab(tabId);
    if (activeSessionId) {
      dispatch(resetChat());
    }
  };

  const showConversation = isSignedIn && Boolean(activeSessionId);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Workspace navigation">
        <div className={styles.brand}>
          <div className={styles.brandTile}>H</div>
          <div>
            <p className={styles.brandName}>Hirable</p>
            <p className={styles.brandTag}>your cv editor</p>
          </div>
        </div>

        <nav className={styles.tabs} aria-label="Workspace tabs">
          {tabs.map((tab, index) => {
            const isActive = !activeSessionId && activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={cx(styles.tab, isActive && styles.tabActive)}
                aria-current={isActive ? "page" : undefined}
                onClick={() => handleTabClick(tab.id)}
              >
                <span className={styles.tabNum}>{`0${index + 1}`}</span>
                <span className={styles.tabText}>
                  <span className={styles.tabLabel}>{tab.label}</span>
                  <span className={styles.tabDetail}>{tab.detail}</span>
                </span>
                {isActive ? <span className={styles.tabDot} /> : null}
              </button>
            );
          })}
        </nav>

        {isSignedIn && (
          <div className={styles.recentChats}>
            <RecentChats />
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
        {showConversation ? (
          <AuthenticatedTab title="Conversation" isLoaded={isLoaded} isSignedIn={isSignedIn}>
            <ConversationPage />
          </AuthenticatedTab>
        ) : (
          renderTab(activeTab, isLoaded, isSignedIn)
        )}
      </main>
    </div>
  );
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

  return (
    <AuthenticatedTab title="Tailor" isLoaded={isLoaded} isSignedIn={isSignedIn}>
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

  return <AuthenticatedApiProvider>{children}</AuthenticatedApiProvider>;
}

function Placeholder({ title, compact = false }: { title: string; compact?: boolean }) {
  return (
    <section className={cx(styles.placeholder, compact && styles.placeholderCompact)}>
      <p className={styles.placeholderEyebrow}>{title}</p>
      <h2 className={styles.placeholderTitle}>{compact ? title : "Coming soon"}</h2>
    </section>
  );
}
