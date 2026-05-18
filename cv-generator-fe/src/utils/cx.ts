/** Joins truthy class names — used to compose CSS Module classes conditionally. */
export const cx = (...classes: Array<string | false | null | undefined>): string =>
  classes.filter(Boolean).join(" ");
