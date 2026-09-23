"use client";

import { useSyncExternalStore } from "react";
import { createPortal } from "react-dom";

const subscribe = () => () => {};

/**
 * Renders the print document as a direct child of <body>.
 *
 * WHY A PORTAL. The workspace is a fixed-height, clipped frame -- the root is
 * `h-[100dvh] overflow-hidden` with three scrolling columns inside it, which is
 * exactly right for a reading station and exactly wrong for paper: anything
 * printed from inside it is clipped to one viewport height, so a two-page
 * report prints as one page and a bit. Fixing that in the print stylesheet
 * means reaching up the tree and neutralising the height and overflow of every
 * ancestor by hand, and that list silently rots the moment the layout changes.
 *
 * A portal sidesteps all of it. The document becomes a sibling of the app, so
 * `@media print` needs exactly two rules: hide the app, show the document.
 *
 * CLIENT ONLY, without a mount effect. `createPortal` needs a real `document`,
 * so this cannot run during the server render. The usual guard is
 * `useState(false)` plus `useEffect(() => setMounted(true))`, which React's own
 * lint rule rejects as a cascading render -- and rightly: "am I on the client"
 * is a question about an external system, which is what useSyncExternalStore is
 * for. The server snapshot is `false`, the client snapshot is `true`, and
 * nothing re-renders in a second pass.
 */
export function PrintPortal({ children }: { children: React.ReactNode }) {
  const isClient = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  if (!isClient) return null;
  return createPortal(children, document.body);
}
