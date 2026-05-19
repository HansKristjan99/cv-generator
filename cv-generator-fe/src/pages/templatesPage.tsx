import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import type { Template } from "../api/templates/getTemplates";
import { cx } from "../utils/cx";
import styles from "./templatesPage.module.css";

const TEMPLATE_META: Record<string, { description: string; tags: string[] }> = {
  default: {
    description: "Compact single-column layout with a subtle rule under each section heading. Fits maximum content on one page.",
    tags: ["Compact", "ATS-friendly", "Single column"],
  },
  harvard_classic: {
    description: "Clean academic style modelled after the Harvard OCS template. Centered headings with a full-width rule below the name.",
    tags: ["Academic", "Classic", "Single column"],
  },
  rover: {
    description: "Two-tone layout with Sepia-colored section rules and a large display-size name. Modern feel for tech and design roles.",
    tags: ["Modern", "Styled", "Single column"],
  },
};

export function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [preferredId, setPreferredId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([apiClient.getTemplates(), apiClient.getUserSettings()])
      .then(([tpls, settings]) => {
        if (cancelled) return;
        setTemplates(tpls);
        setPreferredId(settings.preferred_template_id);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load templates");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const select = async (templateId: string) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await apiClient.updateUserSettings({ preferred_template_id: templateId });
      setPreferredId(updated.preferred_template_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save preference");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>Loading templates…</section>
      </main>
    );
  }

  const activeTemplate = templates.find((t) => t.id === preferredId) ?? templates[0];

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Workspace</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbActive}>Templates</span>
          </div>
          <h1 className={styles.title}>Templates</h1>
          <p className={styles.subtitle}>
            Choose a default CV layout. Your selection is applied on every new generation.
          </p>
        </div>
        {activeTemplate ? (
          <span className={styles.status}>
            <span className={styles.statusDot} />
            {activeTemplate.name}
          </span>
        ) : null}
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.grid}>
        {templates.map((template) => {
          const meta = TEMPLATE_META[template.slug];
          const isActive = template.id === preferredId;
          return (
            <article
              key={template.id}
              className={cx(styles.card, isActive && styles.cardActive)}
            >
              <div className={styles.preview}>
                <TemplatePlaceholder slug={template.slug} />
              </div>
              <div className={styles.cardBody}>
                <div className={styles.cardHead}>
                  <h2 className={styles.cardTitle}>{template.name}</h2>
                  {isActive ? <span className={styles.activeBadge}>Active</span> : null}
                </div>
                {meta ? (
                  <>
                    <p className={styles.cardDescription}>{meta.description}</p>
                    <div className={styles.tags}>
                      {meta.tags.map((tag) => (
                        <span key={tag} className={styles.tag}>{tag}</span>
                      ))}
                    </div>
                  </>
                ) : null}
                <button
                  type="button"
                  className={cx(styles.selectButton, isActive && styles.selectButtonActive)}
                  onClick={() => select(template.id)}
                  disabled={saving || isActive}
                >
                  {isActive ? "Selected" : saving ? "Saving…" : "Use this template"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}

function TemplatePlaceholder({ slug }: { slug: string }) {
  if (slug === "harvard_classic") {
    return <HarvardPreview />;
  }
  if (slug === "rover") {
    return <RoverPreview />;
  }
  return <DefaultPreview />;
}

function DefaultPreview() {
  return (
    <div className={styles.mockCv}>
      <div className={cx(styles.mockLine, styles.mockLineName)} />
      <div className={cx(styles.mockLine, styles.mockLineContact)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineSummaryShort)} />
      <div className={styles.mockRule} />
      <div className={cx(styles.mockLine, styles.mockLineHeading)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={styles.mockRule} />
      <div className={cx(styles.mockLine, styles.mockLineHeading)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
    </div>
  );
}

function HarvardPreview() {
  return (
    <div className={styles.mockCv}>
      <div className={cx(styles.mockLine, styles.mockLineNameCenter)} />
      <div className={styles.mockRuleFull} />
      <div className={cx(styles.mockLine, styles.mockLineContactCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
    </div>
  );
}

function RoverPreview() {
  return (
    <div className={cx(styles.mockCv, styles.mockCvRover)}>
      <div className={cx(styles.mockLine, styles.mockLineNameLarge)} />
      <div className={cx(styles.mockLine, styles.mockLineContactCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingRover)} />
      <div className={styles.mockRuleSepia} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingRover)} />
      <div className={styles.mockRuleSepia} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
    </div>
  );
}
