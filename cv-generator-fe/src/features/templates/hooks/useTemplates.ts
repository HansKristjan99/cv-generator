import { useEffect, useState } from "react";

import { apiClient } from "../../../api/client";
import type { Template } from "../../../api/templates/getTemplates";

export type TemplatesStore = {
  templates: Template[];
  preferredId: string | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  select: (templateId: string) => Promise<void>;
};

export function useTemplates(): TemplatesStore {
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

  return { templates, preferredId, loading, saving, error, select };
}
