import { Button } from "../../../primitives/button";
import { TrashIcon } from "../../../primitives/icons";
import type { BulletDraft, Editor, JobDraft } from "../lib/types";
import styles from "../userMemory.module.css";

type Props = {
  editor: Editor;
  setEditor: (editor: Editor) => void;
  draft: JobDraft;
  bullet: BulletDraft;
  index: number;
};

export function JobBulletEditor({ editor, setEditor, draft, bullet, index }: Props) {
  const update = (field: keyof Omit<BulletDraft, "id">, value: string) => {
    setEditor({
      ...editor,
      draft: {
        ...draft,
        bullets: draft.bullets.map((b, i) => (i === index ? { ...b, [field]: value } : b)),
      },
    });
  };

  const remove = () => {
    setEditor({
      ...editor,
      draft: {
        ...draft,
        bullets: draft.bullets.filter((_, i) => i !== index),
      },
      removedChildIds: bullet.id
        ? [...editor.removedChildIds, bullet.id]
        : editor.removedChildIds,
    });
  };

  return (
    <div className={styles.bulletEditor}>
      <textarea
        className={styles.textarea}
        value={bullet.bullet_points}
        onChange={(event) => update("bullet_points", event.target.value)}
        rows={2}
        placeholder="Achievement or responsibility"
      />
      <input
        className={styles.input}
        value={bullet.relevant_technologies}
        onChange={(event) => update("relevant_technologies", event.target.value)}
        placeholder="Relevant technologies"
      />
      <Button variant="danger" size="sm" onClick={remove} iconBefore={<TrashIcon size={13} />}>
        Remove bullet
      </Button>
    </div>
  );
}
