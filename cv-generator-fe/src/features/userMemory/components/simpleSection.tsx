import type { UserMemory } from "../../../api/user-memory/userMemory";
import { simpleToDraft } from "../lib/itemField";
import type { Editor, MemoryKind, SimpleItem, SimpleSectionConfig } from "../lib/types";
import { NEW_ID } from "../lib/types";
import styles from "../userMemory.module.css";
import { CollapsedCard } from "./collapsedCard";
import { SectionHeader } from "./sectionHeader";
import { SimpleEditor } from "./simpleEditor";

type Props = {
  memory: UserMemory;
  section: SimpleSectionConfig;
  editor: Editor | null;
  setEditor: (editor: Editor | null) => void;
  saveEditor: () => void;
  removeItem: (kind: MemoryKind, id: string) => void;
  saving: boolean;
};

export function SimpleSection({
  memory,
  section,
  editor,
  setEditor,
  saveEditor,
  removeItem,
  saving,
}: Props) {
  const items = memory[section.kind] as SimpleItem[];
  const isAdding = editor?.kind === section.kind && editor.id === NEW_ID;

  return (
    <section className={styles.section}>
      <SectionHeader
        title={section.title}
        eyebrow={section.eyebrow}
        count={items.length}
        addLabel={section.addLabel}
        onAdd={() =>
          setEditor({
            kind: section.kind,
            id: NEW_ID,
            draft: section.blank(),
            removedChildIds: [],
          })
        }
      />
      <div className={styles.itemList}>
        {isAdding && editor ? (
          <SimpleEditor
            section={section}
            editor={editor}
            setEditor={setEditor}
            saveEditor={saveEditor}
            removeItem={removeItem}
            saving={saving}
          />
        ) : null}
        {items.length === 0 && !isAdding ? <p className={styles.empty}>{section.empty}</p> : null}
        {items.map((item) => {
          const isOpen = editor?.kind === section.kind && editor.id === item.id;
          if (isOpen && editor) {
            return (
              <SimpleEditor
                key={item.id}
                section={section}
                editor={editor}
                setEditor={setEditor}
                saveEditor={saveEditor}
                removeItem={removeItem}
                saving={saving}
              />
            );
          }
          return (
            <CollapsedCard
              key={item.id}
              title={section.summary(item)}
              meta={section.meta(item)}
              saving={saving}
              onOpen={() =>
                setEditor({
                  kind: section.kind,
                  id: item.id,
                  draft: simpleToDraft(item, section.fields),
                  removedChildIds: [],
                })
              }
              onDelete={() => removeItem(section.kind, item.id)}
            />
          );
        })}
      </div>
    </section>
  );
}
