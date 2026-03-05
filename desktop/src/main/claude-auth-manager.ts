/**
 * @file claude-auth-manager.ts
 * @description Claude Code credential manager
 *
 * Encapsulates all Claude Code credential operations:
 * - Read OAuth credentials from macOS Keychain / ~/.claude/.credentials.json
 * - Detect CLI installation and login status
 * - Launch `claude auth login` browser login (PTY mode preferred, pipe fallback)
 * - Validate setup-token format
 *
 * References OpenClaw cli-credentials.ts credential reading patterns,
 * references OpenClaw pty.ts @lydell/node-pty usage.
 */

import { execFileSync, execFile, spawn, type ChildProcess } from 'child_process'
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import { promisify } from 'util'
import { getShellEnv } from './shell-env'

const execFileAsync = promisify(execFile)

// ─── node-pty Dynamic Loading ─────────────────────────────
//
// On macOS, claude auth login's localhost OAuth callback may be blocked by the browser
// (HTTPS → HTTP downgrade), requiring users to manually paste the auth code.
// In pipe mode the CLI doesn't read stdin; a real PTY is needed for sendInput() to work.
// Reference: OpenClaw src/process/supervisor/adapters/pty.ts

/** Process handle returned by node-pty spawn */
interface PtyHandle {
  pid: number
  write: (data: string) => void
  onData: (listener: (data: string) => void) => { dispose: () => void } | void
  onExit: (listener: (event: { exitCode: number; signal?: number }) => void) => { dispose: () => void } | void
  kill: (signal?: string) => void
}

/** node-pty spawn function signature */
type PtySpawnFn = (
  file: string,
  args: string[],
  options: {
    name?: string
    cols?: number
    rows?: number
    cwd?: string
    env?: Record<string, string>
  }
) => PtyHandle

/**
 * Dynamically load @lydell/node-pty spawn function
 *
 * Uses try/catch for when not installed, falls back to pipe mode.
 * electron-vite externalizeDepsPlugin preserves require calls,
 * loading native modules from node_modules at runtime.
 */
function getNodePtySpawn(): PtySpawnFn | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod = require('@lydell/node-pty') as Record<string, unknown>
    const spawn = (mod.spawn ?? (mod.default as Record<string, unknown> | undefined)?.spawn) as PtySpawnFn | undefined
    return spawn ?? null
  } catch {
    return null
  }
}

// ─── Type Definitions ───────────────────────────────────────

/** Claude OAuth raw data (structure from credentials.json) */
interface ClaudeOAuthData {
  accessToken: string
  refreshToken?: string
  expiresAt: number
}

/** Authentication status */
export interface ClaudeAuthStatus {
  state: 'logged_in' | 'expired' | 'not_logged_in' | 'cli_not_installed'
  method?: 'oauth' | 'token'
  expiresAt?: number
  isExpired?: boolean
}

/** Complete authentication info */
export interface ClaudeAuthInfo {
  cliInstalled: boolean
  cliVersion: string | null
  authStatus: ClaudeAuthStatus
  hasApiKey: boolean
  hasSetupToken: boolean
}

/** Login process status */
export interface LoginProcessStatus {
  state: 'idle' | 'running' | 'success' | 'failed' | 'timeout'
  message?: string
}

// ─── Constants ─────────────────────────────────────────

const CREDENTIALS_RELATIVE_PATH = '.claude/.credentials.json'
const KEYCHAIN_SERVICE = 'Claude Code-credentials'
const SETUP_TOKEN_PREFIX = 'sk-ant-oat01-'
const SETUP_TOKEN_MIN_LENGTH = 80
const LOGIN_POLL_INTERVAL = 2000
const DEFAULT_LOGIN_TIMEOUT = 120000
/** Timeout for waiting OAuth callback on macOS; prompts manual auth code paste after timeout */
const MACOS_CALLBACK_HINT_DELAY = 20000

// ─── Credential Reading ─────────────────────────────────────

/**
 * Read Claude Code credentials from macOS Keychain
 *
 * Uses the security command to read the password for "Claude Code-credentials" service,
 * parsing the claudeAiOauth field from JSON. macOS only.
 */
function readCredentialsFromKeychain(): ClaudeOAuthData | null {
  if (process.platform !== 'darwin') return null

  try {
    const result = execFileSync(
      'security',
      ['find-generic-password', '-s', KEYCHAIN_SERVICE, '-w'],
      { encoding: 'utf8', timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'] }
    )

    const data = JSON.parse(result.trim())
    return parseOAuthData(data?.claudeAiOauth)
  } catch {
    return null
  }
}

/**
 * Read credentials from ~/.claude/.credentials.json file
 */
function readCredentialsFromFile(): ClaudeOAuthData | null {
  try {
    const credPath = join(homedir(), CREDENTIALS_RELATIVE_PATH)
    if (!existsSync(credPath)) return null

    const content = readFileSync(credPath, 'utf-8')
    const data = JSON.parse(content)
    return parseOAuthData(data?.claudeAiOauth)
  } catch {
    return null
  }
}

/**
 * Parse and validate OAuth data
 */
function parseOAuthData(oauth: unknown): ClaudeOAuthData | null {
  if (!oauth || typeof oauth !== 'object') return null

  const obj = oauth as Record<string, unknown>
  const accessToken = obj.accessToken
  const refreshToken = obj.refreshToken
  const expiresAt = obj.expiresAt

  if (typeof accessToken !== 'string' || !accessToken) return null
  if (typeof expiresAt !== 'number' || !Number.isFinite(expiresAt) || expiresAt <= 0) return null

  return {
    accessToken,
    refreshToken: typeof refreshToken === 'string' && refreshToken ? refreshToken : undefined,
    expiresAt
  }
}

/** Check if credentials have expired */
function isExpired(expiresAt: number): boolean {
  return Date.now() > expiresAt
}

/**
 * Read Claude CLI credentials (main entry point)
 *
 * macOS: Keychain first -> fallback to file
 * Linux: file only
 */
export function readClaudeCredentials(): ClaudeOAuthData | null {
  if (process.platform === 'darwin') {
    const keychainCreds = readCredentialsFromKeychain()
    if (keychainCreds) return keychainCreds
  }
  return readCredentialsFromFile()
}

// ─── Authentication Status Detection ──────────────────────────────────

/**
 * Get complete Claude Code authentication info
 *
 * 1. Detect CLI installation (claude --version, 10s timeout)
 * 2. Read credential files to determine login status (millisecond-level)
 * 3. Check ANTHROPIC_API_KEY in .env
 */
export async function getClaudeAuthInfo(readEnvFn: () => Record<string, string>): Promise<ClaudeAuthInfo> {
  // 1. Detect CLI installation
  let cliInstalled = false
  let cliVersion: string | null = null
  try {
    const { stdout } = await execFileAsync('claude', ['--version'], {
      timeout: 10000,
      env: getShellEnv()
    })
    cliInstalled = true
    cliVersion = stdout.trim().split('\n')[0] || null
  } catch {
    // CLI not installed
  }

  // 2. Read credentials → auth status
  let authStatus: ClaudeAuthStatus
  const creds = readClaudeCredentials()
  if (creds) {
    const expired = isExpired(creds.expiresAt)
    authStatus = {
      state: expired ? 'expired' : 'logged_in',
      method: creds.refreshToken ? 'oauth' : 'token',
      expiresAt: creds.expiresAt,
      isExpired: expired
    }
  } else if (cliInstalled) {
    authStatus = { state: 'not_logged_in' }
  } else {
    authStatus = { state: 'cli_not_installed' }
  }

  // 3. Check API Key in .env
  const envConfig = readEnvFn()
  const apiKey = envConfig.ANTHROPIC_API_KEY?.trim() || ''
  const hasApiKey = !!apiKey
  const hasSetupToken = apiKey.startsWith(SETUP_TOKEN_PREFIX) && apiKey.length >= SETUP_TOKEN_MIN_LENGTH

  return {
    cliInstalled,
    cliVersion,
    authStatus,
    hasApiKey,
    hasSetupToken
  }
}

// ─── One-Click Login ──────────────────────────────────────

/**
 * Launch `claude auth login` browser login flow
 *
 * Hybrid strategy (references OpenClaw):
 * 1. Prefer node-pty for a real pseudo-terminal (auth code input works on macOS)
 * 2. Fall back to pipe mode when node-pty is unavailable (localhost callback usually succeeds on Linux)
 * 3. On macOS, prompt user to manually paste auth code if no new credentials detected within 20s
 *
 * - Poll credential files every 2s to detect login completion
 * - Auto-terminate after 120s timeout
 * - Returns a cancellable handle
 */
export function startClaudeLogin(
  onStatusChange: (status: LoginProcessStatus) => void,
  onUrlDetected?: (url: string) => void,
  timeoutMs: number = DEFAULT_LOGIN_TIMEOUT
): { promise: Promise<LoginProcessStatus>; cancel: () => void; sendInput: (text: string) => void } {
  // ── Process handle (PTY or pipe mode, one or the other) ──
  let ptyHandle: PtyHandle | null = null
  let childProc: ChildProcess | null = null

  // ── Timers ──
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let timeoutTimer: ReturnType<typeof setTimeout> | null = null
  let fallbackHintTimer: ReturnType<typeof setTimeout> | null = null
  let cancelled = false

  const cleanup = () => {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    if (timeoutTimer) { clearTimeout(timeoutTimer); timeoutTimer = null }
    if (fallbackHintTimer) { clearTimeout(fallbackHintTimer); fallbackHintTimer = null }
    if (ptyHandle) {
      try { ptyHandle.kill('SIGTERM') } catch { /* already exited */ }
      ptyHandle = null
    }
    if (childProc) {
      try { childProc.kill('SIGTERM') } catch { /* already exited */ }
      childProc = null
    }
  }

  const cancel = () => {
    cancelled = true
    cleanup()
    onStatusChange({ state: 'failed', message: 'Login cancelled by user' })
  }

  /**
   * Write content to child process (for passing auth code returned by browser)
   *
   * PTY mode: write to PTY stdin (CLI can read normally, \r = Enter)
   * Pipe mode: write to pipe stdin (CLI may not read, but still attempts)
   */
  const sendInput = (text: string) => {
    if (ptyHandle) {
      ptyHandle.write(text + '\r')
    } else if (childProc?.stdin?.writable) {
      childProc.stdin.write(text + '\n')
    }
  }

  const promise = new Promise<LoginProcessStatus>((resolve) => {
    // Record credential state before login (for comparing to detect new credentials)
    const credsBefore = readClaudeCredentials()

    onStatusChange({ state: 'running', message: 'Opening browser for authentication...' })

    // Build child process env: based on shell env, disable color output to simplify URL parsing
    const shellEnv = getShellEnv()
    const spawnEnv: Record<string, string> = {
      ...shellEnv,
      FORCE_COLOR: '0',       // Disable color output to prevent ANSI escape codes from interfering with URL parsing
      NO_COLOR: '1',          // Community-standard no-color flag
      TERM: 'dumb',           // Tell CLI this is not a rich terminal
      HOME: process.env.HOME || homedir()  // Ensure HOME exists (required for Keychain/credential read/write)
    }

    // ── Shared output handling logic ──
    const stripAnsi = (s: string) => s.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, '')
    const urlRegex = /https?:\/\/[^\s\x1B]+/
    let urlOpened = false
    let accumulatedOutput = ''

    const handleOutput = (raw: string) => {
      const text = stripAnsi(raw)
      console.log(`[claude-login] output: ${text.substring(0, 300)}`)
      accumulatedOutput += text

      // Push CLI output to UI in real-time for debugging
      onStatusChange({ state: 'running', message: `CLI: ${text.substring(0, 150).trim() || '(waiting...)'}` })

      if (!urlOpened) {
        const match = text.match(urlRegex)
        if (match) {
          // Strip trailing punctuation that may be attached to URL
          const cleanUrl = match[0].replace(/[)>\]'",;]+$/, '')
          urlOpened = true
          onUrlDetected?.(cleanUrl)
          onStatusChange({ state: 'running', message: 'Browser opened. Waiting for authorization...' })

          // Start fallback hint timer on macOS:
          // OAuth callback may be blocked by browser due to HTTPS→HTTP downgrade,
          // user needs to manually paste the auth code shown on the browser page
          if (process.platform === 'darwin') {
            fallbackHintTimer = setTimeout(() => {
              if (!cancelled) {
                const creds = readClaudeCredentials()
                const isNewCreds = creds && (!credsBefore || creds.accessToken !== credsBefore.accessToken)
                if (!isNewCreds) {
                  onStatusChange({
                    state: 'running',
                    message: 'Paste the auth code from browser into the input box below. Or run `claude setup-token` in terminal.'
                  })
                }
              }
            }, MACOS_CALLBACK_HINT_DELAY)
          }
        }
      }
    }

    /** Shared process exit handler */
    const handleExit = (code: number | null) => {
      clearTimeout(noOutputTimer)
      if (cancelled) return

      // After process exits, do a final URL match from accumulated output (handle chunked transfer)
      if (!urlOpened) {
        const match = accumulatedOutput.match(urlRegex)
        if (match) {
          const cleanUrl = match[0].replace(/[)>\]'",;]+$/, '')
          urlOpened = true
          onUrlDetected?.(cleanUrl)
          onStatusChange({ state: 'running', message: 'Browser opened. Waiting for authorization...' })
          // Don't resolve, continue polling for credentials
          return
        }
      }

      // Final check after process exits normally
      const creds = readClaudeCredentials()
      if (creds && (!credsBefore || creds.accessToken !== credsBefore.accessToken)) {
        cleanup()
        const status: LoginProcessStatus = { state: 'success', message: 'Login successful' }
        onStatusChange(status)
        resolve(status)
      } else if (code !== 0 && code !== null) {
        cleanup()
        const status: LoginProcessStatus = {
          state: 'failed',
          message: `claude login exited with code ${code}. Output: ${accumulatedOutput.substring(0, 200)}`
        }
        onStatusChange(status)
        resolve(status)
      } else {
        // code === 0 but no new credentials detected: may already be logged in, or credential write delay
        if (creds && !isExpired(creds.expiresAt)) {
          cleanup()
          const status: LoginProcessStatus = {
            state: 'success',
            message: 'Already logged in (valid credentials found)'
          }
          onStatusChange(status)
          resolve(status)
        }
        // Otherwise continue polling (credential write may be delayed), eventually timeout
      }
    }

    // ── Launch child process: PTY preferred, pipe fallback ──

    const ptySpawn = getNodePtySpawn()

    if (ptySpawn) {
      // PTY mode: provides a real pseudo-terminal, enabling CLI stdin interaction
      // This way users on macOS can paste auth code via Desktop input field
      try {
        ptyHandle = ptySpawn('claude', ['auth', 'login'], {
          cwd: homedir(),
          env: spawnEnv,
          name: 'dumb',    // TERM=dumb, reduce ANSI output
          cols: 120,
          rows: 30,
        })

        console.log(`[claude-login] spawned with PTY mode (pid=${ptyHandle.pid})`)

        // PTY merges stdout/stderr into a single data stream
        ptyHandle.onData((data: string) => {
          handleOutput(data)
        })

        ptyHandle.onExit((event: { exitCode: number; signal?: number }) => {
          handleExit(event.exitCode)
        })
      } catch (err) {
        // PTY spawn failed (e.g. claude not installed), report error immediately
        if (!cancelled) {
          cleanup()
          const status: LoginProcessStatus = {
            state: 'failed',
            message: `Failed to start claude login (PTY): ${err instanceof Error ? err.message : String(err)}`
          }
          onStatusChange(status)
          resolve(status)
        }
        return
      }
    } else {
      // Pipe mode fallback: use standard child_process when node-pty is unavailable
      // On Linux, localhost callback usually succeeds automatically, no manual auth code paste needed
      console.log('[claude-login] node-pty not available, falling back to pipe mode')

      childProc = spawn('claude', ['auth', 'login'], {
        env: spawnEnv,
        cwd: homedir(),
        stdio: ['pipe', 'pipe', 'pipe']
      })

      childProc.stdout?.on('data', (d: Buffer) => handleOutput(d.toString()))
      childProc.stderr?.on('data', (d: Buffer) => handleOutput(d.toString()))

      childProc.on('error', (err) => {
        if (cancelled) return
        clearTimeout(noOutputTimer)
        cleanup()
        const status: LoginProcessStatus = {
          state: 'failed',
          message: `Failed to start claude login: ${err.message}`
        }
        onStatusChange(status)
        resolve(status)
      })

      childProc.on('exit', (code) => {
        handleExit(code)
      })
    }

    // ── 5s no-output warning ──
    const noOutputTimer = setTimeout(() => {
      if (!urlOpened && !cancelled) {
        onStatusChange({
          state: 'running',
          message: accumulatedOutput
            ? `No URL found in output: ${accumulatedOutput.substring(0, 150)}`
            : 'claude login produced no output after 5s'
        })
      }
    }, 5000)

    // ── Poll for credential changes ──
    pollTimer = setInterval(() => {
      if (cancelled) return
      const creds = readClaudeCredentials()
      if (creds && (!credsBefore || creds.accessToken !== credsBefore.accessToken)) {
        cleanup()
        const status: LoginProcessStatus = { state: 'success', message: 'Login successful' }
        onStatusChange(status)
        resolve(status)
      }
    }, LOGIN_POLL_INTERVAL)

    // ── Timeout handling ──
    timeoutTimer = setTimeout(() => {
      if (cancelled) return
      cleanup()
      const status: LoginProcessStatus = {
        state: 'timeout',
        message: `Login timed out after ${timeoutMs / 1000}s. Please try again.`
      }
      onStatusChange(status)
      resolve(status)
    }, timeoutMs)
  })

  return { promise, cancel, sendInput }
}

// ─── Setup Token Validation ──────────────────────────────

/**
 * Validate setup-token format
 *
 * Format requirements: starts with sk-ant-oat01-, at least 80 characters
 */
export function validateSetupToken(token: string): { valid: boolean; message: string } {
  const trimmed = token.trim()
  if (!trimmed) {
    return { valid: false, message: 'Token is empty' }
  }
  if (!trimmed.startsWith(SETUP_TOKEN_PREFIX)) {
    return { valid: false, message: `Token must start with ${SETUP_TOKEN_PREFIX}` }
  }
  if (trimmed.length < SETUP_TOKEN_MIN_LENGTH) {
    return { valid: false, message: `Token is too short (minimum ${SETUP_TOKEN_MIN_LENGTH} characters)` }
  }
  return { valid: true, message: 'Token format is valid' }
}
