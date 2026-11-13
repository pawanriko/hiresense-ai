// InsForge client — the only place that knows about InsForge auth.
//
// HOW IT WORKS: the browser talks to InsForge directly (a different
// origin — the project's *.insforge.app URL) through the official
// SDK. Sign-in returns an access token that lives IN MEMORY (never
// localStorage) plus a refresh token in an httpOnly cookie on the
// InsForge origin. On page load, the SDK uses that cookie to
// silently restore the session, so a reload does not sign the user
// out. Django never sees the password — it only ever sees the access
// token, as an Authorization: Bearer header, which api.js attaches
// (see api/insforge_auth.py on the server side).
//
// TOKEN TRACKING: the SDK keeps its access token internal — its
// public auth API has no "give me the token" method. So this module
// tracks the token itself, capturing `data.accessToken` from every
// SDK response that returns one (sign-in, sign-up, refresh). The one
// gap is startup: getCurrentUser() proves the session but returns no
// token, so initInsforgeSession() follows it with an explicit
// refreshSession() to capture a token from the cookie. One extra
// round-trip per signed-in page load; the alternative (reaching into
// the SDK's internals) would break on any SDK update.
//
// INSFORGE_MODE is a BUILD-TIME switch: it is on only when both Vite
// env vars are set (VITE_INSFORGE_URL + VITE_INSFORGE_ANON_KEY).
// Without them the app runs the old Django session flow untouched —
// that is the dual-auth window (Phase 2) and the rollback path
// (unset the vars, redeploy). The anon key is public by design
// (InsForge's own docs call it browser-safe); it only identifies the
// project, it grants no user data.
import { createClient } from '@insforge/sdk'

export const INSFORGE_MODE = Boolean(
  import.meta.env.VITE_INSFORGE_URL && import.meta.env.VITE_INSFORGE_ANON_KEY,
)

let client = null
export function getInsforgeClient() {
  if (!INSFORGE_MODE) return null
  if (!client) {
    client = createClient({
      baseUrl: import.meta.env.VITE_INSFORGE_URL,
      anonKey: import.meta.env.VITE_INSFORGE_ANON_KEY,
    })
  }
  return client
}

// The access token this module tracks (see TOKEN TRACKING above).
// Module-level on purpose: exactly one token per page load, shared
// by api.js and the pages, gone on reload until init restores it.
let accessToken = null

function capture(data) {
  if (data?.accessToken) accessToken = data.accessToken
}

// Startup handshake: finishes the OAuth callback exchange if this
// page load IS one (?insforge_code=...), then restores the session
// from the refresh cookie if there is one. Returns the InsForge user
// or null. App.jsx awaits this before asking Django who is signed in.
//
// SINGLE-FLIGHT: concurrent callers share one promise. React's dev
// double-mount (and any future double boot) must not run two refresh
// sequences at once — refresh ROTATES the refresh token, so a racing
// second refresh can lose to the first and report "signed out" for a
// session that is perfectly alive.
let initPromise = null
export function initInsforgeSession() {
  if (!initPromise) initPromise = doInitInsforgeSession()
  return initPromise
}

async function doInitInsforgeSession() {
  const insforge = getInsforgeClient()
  if (!insforge) return null
  const { data, error } = await insforge.auth.getCurrentUser()
  if (error || !data?.user) return null
  // getCurrentUser returns no token, so mint one from the cookie.
  // One retry: a racing refresh (another tab) may have rotated the
  // cookie between the two calls; the retry reads the fresh cookie.
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const refreshed = await insforge.auth.refreshSession()
    if (!refreshed.error && refreshed.data?.accessToken) {
      capture(refreshed.data)
      return refreshed.data.user ?? data.user
    }
  }
  return null
}

// The current access token for Django API calls, or null when signed
// out. Does NOT refresh — api.js refreshes (once) on a 401 instead,
// so an expired token costs one retry, not a check on every call.
export function getAccessToken() {
  return accessToken
}

// Mint a fresh access token from the refresh cookie. True when a new
// token is now in memory.
export async function refreshInsforgeSession() {
  const insforge = getInsforgeClient()
  if (!insforge) return false
  const { data, error } = await insforge.auth.refreshSession()
  capture(data)
  return !error && Boolean(data?.accessToken)
}

function throwIfError(error, fallback) {
  if (error) throw new Error(error.message || fallback)
}

export async function insforgeSignIn(email, password) {
  const { data, error } = await getInsforgeClient().auth.signInWithPassword({
    email,
    password,
  })
  throwIfError(error, 'Sign-in failed')
  capture(data)
  return data.user
}

export async function insforgeSignUp(email, password, name) {
  const { data, error } = await getInsforgeClient().auth.signUp({
    email,
    password,
    name: name || undefined,
  })
  throwIfError(error, 'Sign-up failed')
  // Email verification is OFF for this project (see the swap plan),
  // so signup signs straight in. If it is ever turned on, the token
  // is null here and the user must verify first — say so plainly
  // instead of landing them on a broken dashboard.
  if (data?.requireEmailVerification || !data?.accessToken) {
    throw new Error('Please verify your email, then sign in.')
  }
  capture(data)
  return data.user
}

export async function insforgeSignOut() {
  accessToken = null
  initPromise = null
  const insforge = getInsforgeClient()
  if (insforge) await insforge.auth.signOut()
}

// Google sign-in: the SDK redirects to Google, Google redirects back
// to /login with ?insforge_code=..., and the SDK exchanges it for a
// session automatically on the next page load (see
// initInsforgeSession). The redirect URL must be allowlisted in the
// InsForge project (allowed_redirect_urls) or InsForge refuses it.
export async function insforgeSignInWithGoogle() {
  await getInsforgeClient().auth.signInWithOAuth('google', {
    redirectTo: `${window.location.origin}/login`,
  })
}
