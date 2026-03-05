/**
 * @file shell-env.ts
 * @description Login shell environment variable resolver
 *
 * When launching .app on macOS via double-click, Electron only inherits launchd's minimal env vars,
 * PATH, API Keys, etc. set in ~/.zshrc and similar configs are all invisible.
 *
 * This module runs the user's login shell once at startup (`shell -ilc 'env -0'`),
 * parses the complete env vars and caches them for all child processes.
 * Linux uses process.env directly (terminal launch inherits full environment).
 */

import { execFile } from 'child_process'
import { promisify } from 'util'
import { join } from 'path'

const execFileAsync = promisify(execFile)

/** Cached environment variables */
let cachedEnv: Record<string, string> | null = null

/**
 * Called once at startup to parse and cache the user's login shell environment variables.
 * Only executes shell resolution on macOS; Linux uses process.env directly.
 */
export async function initShellEnv(): Promise<void> {
  if (process.platform !== 'darwin') {
    // Linux: terminal launch inherits full environment, use directly
    cachedEnv = { ...process.env } as Record<string, string>
    console.log(`[shell-env] Linux detected, using process.env (${Object.keys(cachedEnv).length} vars)`)
    return
  }

  try {
    const shell = process.env.SHELL || '/bin/zsh'
    console.log(`[shell-env] Resolving login shell env via: ${shell}`)

    const { stdout } = await execFileAsync(shell, ['-ilc', 'env -0'], {
      timeout: 10000,
      env: process.env,
      // Avoid stdin blocking
      maxBuffer: 10 * 1024 * 1024
    })

    // NUL-delimited parsing (env -0 outputs KEY=VALUE\0KEY=VALUE\0...)
    const parsed: Record<string, string> = {}
    const entries = stdout.split('\0')
    for (const entry of entries) {
      if (!entry) continue
      const eqIndex = entry.indexOf('=')
      if (eqIndex === -1) continue
      const key = entry.substring(0, eqIndex)
      const value = entry.substring(eqIndex + 1)
      parsed[key] = value
    }

    cachedEnv = parsed
    console.log(`[shell-env] Resolved ${Object.keys(cachedEnv).length} vars from login shell`)
  } catch (err) {
    console.warn(`[shell-env] Failed to resolve login shell env, using fallback:`, err)
    cachedEnv = buildFallbackEnv()
    console.log(`[shell-env] Fallback env has ${Object.keys(cachedEnv).length} vars`)
  }
}

/**
 * Synchronously get cached env vars, used as env parameter for all child processes.
 * Returns fallback env if initShellEnv hasn't been called yet.
 */
export function getShellEnv(): Record<string, string> {
  if (cachedEnv) return cachedEnv
  // Use fallback when not yet initialized (shouldn't happen, but defensive)
  console.warn('[shell-env] getShellEnv() called before initShellEnv(), using fallback')
  cachedEnv = buildFallbackEnv()
  return cachedEnv
}

/** Build fallback env: process.env + common tool paths */
function buildFallbackEnv(): Record<string, string> {
  const home = process.env.HOME || ''
  // Docker Desktop bin MUST come first — on Intel Mac, Homebrew's /usr/local/bin/docker
  // is a CLI-only binary without compose plugin; Docker Desktop's docker has compose built in.
  const extraPaths = [
    '/Applications/Docker.app/Contents/Resources/bin',
    '/usr/local/bin',
    '/opt/homebrew/bin',
    join(home, '.local', 'bin'),            // Claude Code CLI default install path (~/.local/bin/claude)
    join(home, '.cargo', 'bin'),
    join(home, '.nvm', 'versions', 'node'),  // nvm common path
  ]
  const currentPath = process.env.PATH || '/usr/bin:/bin'
  const enhancedPath = [...extraPaths, currentPath].join(':')

  return {
    ...(process.env as Record<string, string>),
    PATH: enhancedPath
  }
}
