/**
 * Decide what a background refresh should do to the rendered lecture catalog.
 * - clear: no user or no learning permission -> hide private content at once
 * - keep: same user and identical rows -> leave the DOM (open series, material panels, scroll) alone
 * - render: rows or user changed -> rebuild, then restore the view
 */
export function catalogSignature(userId, rows) {
  return JSON.stringify([userId, rows]);
}

export function catalogPlan({ prev, userId, rows, canLearn, rendered }) {
  if (!userId || !canLearn) return { action: "clear", signature: "" };
  const signature = catalogSignature(userId, rows);
  if (rendered && prev === signature) return { action: "keep", signature };
  return { action: "render", signature };
}
