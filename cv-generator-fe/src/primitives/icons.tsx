import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { size?: number };

function svgBase({ size = 16, ...rest }: Props) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    ...rest,
  };
}

export function TrashIcon(props: Props) {
  return (
    <svg {...svgBase(props)}>
      <path d="M4 7h16" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
      <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

export function CloseIcon(props: Props) {
  return (
    <svg {...svgBase(props)}>
      <path d="M6 6l12 12" />
      <path d="M18 6L6 18" />
    </svg>
  );
}

export function DownloadIcon(props: Props) {
  return (
    <svg {...svgBase(props)}>
      <path d="M12 4v12" />
      <path d="M6 12l6 6 6-6" />
      <path d="M4 20h16" />
    </svg>
  );
}
