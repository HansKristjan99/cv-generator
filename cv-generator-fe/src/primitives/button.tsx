import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cx } from "../utils/cx";
import styles from "./button.module.css";

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
