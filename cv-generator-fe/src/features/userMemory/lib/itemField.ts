import type { FieldConfig, SimpleItem } from "./types";

export function itemField(item: SimpleItem, field: string): string {
  const value = (item as unknown as Record<string, string | null>)[field];
  return value ?? "";
}

export function simpleToDraft(
  item: SimpleItem,
  fields: FieldConfig[],
): Record<string, string> {
  return {
    id: item.id,
    ...Object.fromEntries(fields.map((field) => [field.name, itemField(item, field.name)])),
  };
}

export function dates(start: string | null, end: string | null): string {
  return [start, end].filter(Boolean).join(" - ");
}
