export const TEMPLATE_META: Record<string, { description: string; tags: string[] }> = {
  default: {
    description:
      "Compact single-column layout with a subtle rule under each section heading. Fits maximum content on one page.",
    tags: ["Compact", "ATS-friendly", "Single column"],
  },
  harvard_classic: {
    description:
      "Clean academic style modelled after the Harvard OCS template. Centered headings with a full-width rule below the name.",
    tags: ["Academic", "Classic", "Single column"],
  },
  rover: {
    description:
      "Two-tone layout with Sepia-colored section rules and a large display-size name. Modern feel for tech and design roles.",
    tags: ["Modern", "Styled", "Single column"],
  },
};
