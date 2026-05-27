import { cx } from "../../../utils/cx";
import { canSave } from "../lib/canSave";
import type { Editor, MemoryKind, SimpleSectionConfig } from "../lib/types";
import { NEW_ID } from "../lib/types";
import styles from "../userMemory.module.css";
import { EditorActions } from "./editorActions";
import { Field } from "./field";

type Props = {
  section: SimpleSectionConfig;
  editor: Editor;
  setEditor: (editor: Editor | null) => void;
  saveEditor: () => void;
  removeItem: (kind: MemoryKind, id: string) => void;
  saving: boolean;
};

export function SimpleEditor({ section, editor, setEditor, saveEditor, removeItem, saving }: Props) {
  const draft = editor.draft as Record<string, string>;
  return (
    <article className={cx(styles.itemCard, styles.itemCardOpen)} key={`${section.kind}:${editor.id}`}>
      <div className={styles.editorHead}>
        <div>
          <p className={styles.editorEyebrow}>{editor.id === NEW_ID ? "New" : "Editing"}</p>
          <h3 className={styles.editorTitle}>{section.title}</h3>
        </div>
      </div>

      <div className={styles.fieldGrid}>
        {section.fields.map((field) => (
          <Field
            key={field.name}
            field={field}
            value={draft[field.name] ?? ""}
            onChange={(value) =>
              setEditor({ ...editor, draft: { ...draft, [field.name]: value } })
            }
          />
        ))}
      </div>

      <EditorActions
        canSave={canSave(editor)}
        saving={saving}
        canRemove={editor.id !== NEW_ID}
        onSave={saveEditor}
        onCancel={() => setEditor(null)}
        onRemove={() => removeItem(section.kind, editor.id)}
      />
    </article>
  );
}
