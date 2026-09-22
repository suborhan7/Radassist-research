import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export type Variant = "primary" | "secondary" | "ghost" | "danger";
export type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  block?: boolean;
}

/**
 * "Reading Room" button. Two accents, each with one job: cyan solid is the
 * single primary action per view; bordered/ghost are quiet. There is no red in
 * this theme, so `danger` reads as amber (attention) rather than a third hue.
 * Transitions are colour-only and honour the reduced-motion token globally.
 */
export const BUTTON_BASE =
  "inline-flex items-center justify-center gap-8 rounded-field font-medium whitespace-nowrap " +
  // Tactile press feedback (Feedback, ~120ms, inside the press budget); the
  // scale rides the same duration-hover as colour. Reduced motion neutralizes
  // it globally via tokens.css. disabled has no press.
  "transition-[color,background-color,filter,transform] duration-hover " +
  "active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100";

/**
 * Every variant now carries a surface and a colour, because the quiet ones did
 * not read as buttons at all.
 *
 * `secondary` was `border-strong` + `text-text-secondary` with no fill: a thin
 * grey outline around grey caption text on a near-black page. Next to a solid
 * cyan primary it disappeared, and "Compare previous" was reported as not
 * looking like something you could press. It is now a cyan OUTLINE button --
 * the accent this product already uses for interaction, in its wash-and-line
 * form. Hierarchy is carried by fill rather than by hue: solid cyan is the one
 * primary action per view, cyan-on-wash is a real but secondary action, and
 * they stay trivially distinguishable side by side.
 *
 * `ghost` keeps the neutral ramp -- it is the variant for actions that are
 * genuinely not offers (the out-of-scope Download PDF) -- but it gets a border
 * and a fill so it reads as a control in a disabled state rather than as a
 * stray line of text.
 *
 * Still two accents. Nothing here introduces a third hue, and `danger` remains
 * amber because this theme has no red.
 */
export const VARIANT: Record<Variant, string> = {
  primary: "bg-cyan text-cyan-ink font-semibold hover:brightness-110",
  secondary:
    "border border-cyan-line bg-cyan-wash text-cyan hover:bg-cyan hover:text-cyan-ink hover:border-cyan",
  ghost: "border border-strong bg-bg-hover text-text-primary hover:border-cyan-line hover:text-cyan",
  danger: "bg-amber text-amber-ink font-semibold hover:brightness-110",
};

// One primary per view. Heights come from the spacing scale (h-N == var(--space-N)).
export const SIZE: Record<Size, string> = {
  sm: "h-34 px-14 text-sm",
  md: "h-38 px-16 text-sm",
  lg: "h-46 px-22 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", loading, block, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(BUTTON_BASE, VARIANT[variant], SIZE[size], block && "w-full", className)}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
});

/** Stage tick, not decoration: waiting is honest work here (§10.9). */
function Spinner() {
  return (
    <svg className="h-16 w-16 animate-spin" viewBox="0 0 16 16" fill="none" aria-hidden>
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeOpacity=".25" strokeWidth="2" />
      <path d="M14.5 8A6.5 6.5 0 0 0 8 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
