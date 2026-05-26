import { useEffect, useState } from "react";

import { apiClient } from "../../../api/client";
import type { UserMemory, UserMemoryPatch } from "../../../api/user-memory/userMemory";
import { buildPatch } from "../lib/buildPatch";
import { canSave } from "../lib/canSave";
import type { Editor, MemoryKind } from "../lib/types";

export type UserMemoryStore = {
  memory: UserMemory | null;
  editor: Editor | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  setEditor: (editor: Editor | null) => void;
  saveEditor: () => Promise<void>;
  removeItem: (kind: MemoryKind, id: string) => Promise<void>;
  addSkill: (name: string) => Promise<void>;
};

export function useUserMemory(): UserMemoryStore {
  const [memory, setMemory] = useState<UserMemory | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void apiClient
      .getUserMemory()
      .then((data) => {
        if (!cancelled) setMemory(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load memory");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const apply = async (patch: UserMemoryPatch, errMsg: string) => {
    setSaving(true);
    setError(null);
    try {
      const next = await apiClient.updateUserMemory(patch);
      setMemory(next);
      setEditor(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : errMsg);
    } finally {
      setSaving(false);
    }
  };

  const saveEditor = async () => {
    if (!editor || !canSave(editor)) return;
    await apply(buildPatch(editor), "Unable to save memory");
  };

  const removeItem = async (kind: MemoryKind, id: string) => {
    if (!id) return;
    await apply({ [kind]: [{ id, delete: true }] }, "Unable to remove memory");
  };

  const addSkill = async (name: string) => {
    setSaving(true);
    setError(null);
    try {
      const next = await apiClient.updateUserMemory({ skills: [{ name }] });
      setMemory(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save memory");
    } finally {
      setSaving(false);
    }
  };

  return { memory, editor, loading, saving, error, setEditor, saveEditor, removeItem, addSkill };
}
