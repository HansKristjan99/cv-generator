import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cx } from "../utils/cx";
import styles from "./button.module.css";
import { DownloadIcon } from "./icons";

export type ButtonVariant = "primary" | "secondary" | "danger" | "dangerSolid";
export type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconBefore?: ReactNode;
};

export function Button({
  variant = "secondary",
  size = "md",
  iconBefore,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  const sizeClass =
    size === "sm" ? styles.sizeSm : size === "lg" ? styles.sizeLg : styles.sizeMd;
  return (
    <button
      type={type}
      className={cx(styles.btn, sizeClass, styles[variant], className)}
      {...rest}
    >
      {iconBefore}
      {children}
    </button>
  );
}

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "neutral" | "danger";
  size?: "sm" | "md";
  label: string;
};

type DownloadButtonProps = {
  size?: ButtonSize;
  disabled?: boolean;
  label?: string;
  className?: string;
  onClick?: () => void;
  href?: string;
  downloadName?: string;
};

export function DownloadButton({
  size = "sm",
  disabled,
  label = "Download",
  className,
  onClick,
  href,
  downloadName,
}: DownloadButtonProps) {
  const sizeClass =
    size === "sm" ? styles.sizeSm : size === "lg" ? styles.sizeLg : styles.sizeMd;
  const icon = <DownloadIcon size={14} />;
  if (href && !disabled) {
    return (
      <a
        className={cx(styles.btn, sizeClass, styles.secondary, className)}
        href={href}
        download={downloadName}
      >
        {icon}
        {label}
      </a>
    );
  }
  return (
    <Button
      variant="secondary"
      size={size}
      disabled={disabled}
      onClick={onClick}
      iconBefore={icon}
      className={className}
    >
      {label}
    </Button>
  );
}

export function IconButton({
  tone = "neutral",
  size = "md",
  label,
  className,
  children,
  type = "button",
  ...rest
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cx(
        styles.iconBtn,
        size === "sm" && styles.iconBtnSm,
        tone === "danger" ? styles.iconBtnDanger : styles.iconBtnNeutral,
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
