"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * A boolean the UI remembers for one doctor, in this browser only.
 *
 * This is the FIRST use of localStorage in the app, so the choice is stated
 * rather than assumed. Theme and language both persist to cookies
 * (lib/theme/index.tsx, lib/i18n/index.tsx) because the *server* layout reads
 * them to stamp <html> before the first paint -- without that the reader gets
 * a flash of the wrong palette. Panel collapse has no such problem: nothing
 * server-rendered depends on it, and sending it to the server on every request
 * would put a purely local viewing preference into the request the backend
 * authenticates with, for no benefit. localStorage keeps it where it belongs.
 *
 * It is never sent to the backend. There is no endpoint for it and none is
 * added -- a doctor's panel state is not clinical data, and the report
 * workspace's network surface stays exactly what it was.
 *
 * KEY NAMESPACING. `rr:` matches the `rr_theme` / `rr_lang` cookie prefix
 * already in use, `v1` leaves room to change the stored shape without reading
 * a stale value as if it were current, and `scope` is the doctor id -- two
 * doctors sharing a workstation must not inherit each other's layout. A null
 * scope (the id has not loaded yet, or nobody is signed in) falls back to
 * memory for the session and touches no storage at all. Writing under a shared
 * "anonymous" key would leak one doctor's preference to the next, which is the
 * one thing per-user persistence is for.
 *
 * WHY useSyncExternalStore AND NOT useState + useEffect. localStorage is an
 * external store, and this is the hook React provides for reading one. The
 * obvious alternative -- default in useState, adopt the stored value in an
 * effect -- is a cascading render on every mount, and React's own lint rule
 * (react-hooks/set-state-in-effect) rejects it. This also gets the two hard
 * parts right by construction: `getServerSnapshot` returns the default, so
 * server HTML and the client's first paint agree and there is no hydration
 * mismatch; and subscribing to `storage` means a doctor with the workspace
 * open in two tabs sees one collapse in both rather than watching them drift.
 *
 * Every storage access is wrapped. localStorage throws outright in a Safari
 * private window and when site data is blocked by policy. On a failed read the
 * default is used; on a failed write the value is held in memory, so the
 * toggle still works for this session and simply is not remembered. Failing
 * the interaction because we cannot record it would be the worse trade.
 */
export function persistedToggleKey(scope: string, name: string): string {
  return `rr:v1:${scope}:${name}`;
}

/** Session fallback: unscoped preferences, and browsers that refuse storage. */
const memory = new Map<string, string>();

const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  // Cross-tab: `storage` fires in the OTHER tabs when one of them writes.
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * Precedence matters and is easy to get backwards: when localStorage is
 * READABLE, its answer is authoritative even when that answer is `null`.
 * `null` means "this doctor has expressed no preference", which is a fact, not
 * a failed lookup -- falling back to the memory map there would let a value
 * from earlier in the session outlive the storage it was supposed to mirror,
 * and the doctor's actual stored choice would be shadowed by a stale one.
 * Memory is consulted only when storage is unusable, or when there is no
 * doctor to scope a key to.
 */
function read(key: string, persist: boolean): string | null {
  if (persist) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return memory.get(key) ?? null;
    }
  }
  return memory.get(key) ?? null;
}

function write(key: string, value: string, persist: boolean): void {
  if (persist) {
    try {
      window.localStorage.setItem(key, value);
      emit();
      return;
    } catch {
      // Storage refused the write: hold it in memory instead, so the toggle
      // still works for this session and simply is not remembered.
    }
  }
  memory.set(key, value);
  emit();
}

export function usePersistedToggle(
  scope: string | null,
  name: string,
  defaultValue: boolean,
): [boolean, (next: boolean) => void] {
  const persist = scope !== null;
  const key = persist ? persistedToggleKey(scope, name) : `memory:${name}`;

  const stored = useSyncExternalStore(
    subscribe,
    () => read(key, persist),
    // Server render: nothing is stored, so the default is what the HTML says.
    () => null,
  );

  // Only the two values this hook writes are honoured. Anything else -- a
  // half-written entry, or a key another feature happened to reuse -- falls
  // back to the default rather than being coerced by truthiness.
  const value = stored === "true" ? true : stored === "false" ? false : defaultValue;

  const set = useCallback(
    (next: boolean) => {
      write(key, String(next), persist);
    },
    [key, persist],
  );

  return [value, set];
}
