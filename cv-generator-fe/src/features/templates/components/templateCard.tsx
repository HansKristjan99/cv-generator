import type { Template } from "../../../api/templates/getTemplates";
import { cx } from "../../../utils/cx";
import { TEMPLATE_META } from "../lib/templateMeta";
import styles from "../templates.module.css";
import { TemplatePlaceholder } from "./templatePreviews";

type Props = {
  template: Template;
  isActive: boolean;
  saving: boolean;
  onSelect: () => void;
};

export function TemplateCard({ template, isActive, saving, onSelect }: Props) {
  const meta = TEMPLATE_META[template.slug];
  return (
    <article className={cx(styles.card, isActive && styles.cardActive)}>
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
                <span key={tag} className={styles.tag}>
                  {tag}
                </span>
              ))}
            </div>
          </>
        ) : null}
        <button
          type="button"
          className={cx(styles.selectButton, isActive && styles.selectButtonActive)}
          onClick={onSelect}
          disabled={saving || isActive}
        >
          {isActive ? "Selected" : saving ? "Saving…" : "Use this template"}
        </button>
      </div>
    </article>
  );
}
