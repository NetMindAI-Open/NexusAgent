/**
 * @file preflight-runner.ts
 * @description Phase 1: Parallel preflight checks for all dependencies
 *
 * Runs all checks concurrently (< 10s total). Detects Docker state at
 * a fine-grained level (not_installed / not_running / starting / healthy)
 * to prevent misdiagnosis of the daemon initializing as "needs privileged install".
 */

import { execFile } from 'child_process'
import { promisify } from 'util'
import { getShellEnv } from './shell-env'
import { detectDockerState } from './docker-manager'
import type { PreflightItem, PreflightResult, SystemInfo, DockerState } from '../shared/setup-types'

const execFileAsync = promisify(execFile)

// ─── Utilities ───────────────────────────────────────

async function execSafe(
  cmd: string,
  args: string[],
  timeout = 10000
): Promise<{ stdout: string; success: boolean }> {
  try {
    const { stdout } = await execFileAsync(cmd, args, {
      timeout,
      env: getShellEnv()
    })
    return { stdout: stdout.trim(), success: true }
  } catch {
    return { stdout: '', success: false }
  }
}

// ─── Individual Checks ───────────────────────────────

async function checkDocker(): Promise<PreflightItem> {
  const state: DockerState = await detectDockerState()

  const hintMap: Record<DockerState, string> = {
    not_installed: 'Docker is not installed. Please download from https://docker.com/products/docker-desktop',
    not_running: 'Docker is installed but not running. Please start Docker Desktop.',
    starting: 'Docker daemon is starting up, please wait...',
    healthy: ''
  }

  let version: string | undefined
  if (state !== 'not_installed') {
    const v = await execSafe('docker', ['--version'], 5000)
    version = v.stdout.match(/Docker version (\S+)/)?.[1]?.replace(/,$/, '')
  }

  return {
    id: 'docker',
    label: 'Docker',
    status: state === 'healthy' ? 'ok' : state === 'starting' ? 'warning' : 'missing',
    version,
    hint: hintMap[state],
    canAutoInstall: state !== 'healthy',
    manualUrl: 'https://www.docker.com/products/docker-desktop/',
    dockerState: state
  }
}

async function checkUv(): Promise<PreflightItem> {
  const r = await execSafe('uv', ['--version'])
  const version = r.stdout.match(/uv (\S+)/)?.[1]
  return {
    id: 'uv',
    label: 'uv (Python package manager)',
    status: version ? 'ok' : 'missing',
    version,
    hint: version ? undefined : 'uv is not installed. It will be installed automatically.',
    canAutoInstall: true,
    manualUrl: 'https://docs.astral.sh/uv/getting-started/installation/'
  }
}

async function checkNode(): Promise<PreflightItem> {
  const r = await execSafe('node', ['--version'])
  const version = r.stdout.replace(/^v/, '') || undefined
  const major = version ? parseInt(version.split('.')[0], 10) : 0
  const ok = major >= 20
  return {
    id: 'node',
    label: 'Node.js (>=20)',
    status: ok ? 'ok' : 'missing',
    version,
    hint: ok ? undefined : 'Node.js >= 20 is required. Download from https://nodejs.org',
    canAutoInstall: false,
    manualUrl: 'https://nodejs.org/en/download/'
  }
}

async function checkClaude(): Promise<PreflightItem> {
  const r = await execSafe('claude', ['--version'])
  const version = r.stdout || undefined
  return {
    id: 'claude',
    label: 'Claude Code CLI',
    status: version ? 'ok' : 'missing',
    version,
    hint: version ? undefined : 'Claude Code CLI not found. It will be installed automatically.',
    canAutoInstall: true
  }
}

async function checkPython(): Promise<PreflightItem> {
  const r = await execSafe('uv', ['run', 'python', '--version'])
  const version = r.stdout.match(/Python (\S+)/)?.[1]
  const ok = (() => {
    if (!version) return false
    const [major, minor] = version.split('.').map(Number)
    return major > 3 || (major === 3 && minor >= 13)
  })()
  return {
    id: 'python',
    label: 'Python (>=3.13)',
    status: ok ? 'ok' : version ? 'warning' : 'missing',
    version,
    hint: ok ? undefined : 'Python >= 3.13 is required. uv will manage it automatically after installation.',
    canAutoInstall: false
  }
}

// ─── System Info ───────────────────────────────────────

async function getSystemInfo(): Promise<SystemInfo> {
  // Total memory
  const os = require('os')
  const totalMemoryGb = Math.round(os.totalmem() / (1024 * 1024 * 1024) * 10) / 10

  // Disk space
  let freeDiskGb = -1
  try {
    const { stdout } = await execFileAsync('df', ['-k', '/'], { timeout: 5000 })
    const lines = stdout.trim().split('\n')
    if (lines.length >= 2) {
      const parts = lines[1].split(/\s+/)
      // df -k: Available column index varies, typically 3rd column
      const availKb = parseInt(parts[3], 10)
      if (!isNaN(availKb)) {
        freeDiskGb = Math.round(availKb / 1024 / 1024 * 10) / 10
      }
    }
  } catch { /* ignore */ }

  // Network check (simple DNS / HTTP connectivity)
  let networkOk = false
  try {
    await execFileAsync('curl', ['-sf', '--max-time', '5', '-o', '/dev/null', 'https://registry.hub.docker.com/v2/'], {
      timeout: 8000,
      env: getShellEnv()
    })
    networkOk = true
  } catch { /* offline or blocked */ }

  return {
    platform: process.platform,
    arch: process.arch,
    totalMemoryGb,
    freeDiskGb,
    networkOk
  }
}

// ─── Public API ───────────────────────────────────────

export async function runPreflight(): Promise<PreflightResult> {
  // Run all checks in parallel for speed
  const [docker, uv, node, claude, python, systemInfo] = await Promise.all([
    checkDocker(),
    checkUv(),
    checkNode(),
    checkClaude(),
    checkPython(),
    getSystemInfo()
  ])

  const items = [docker, uv, node, claude, python]

  // All required deps ready? (docker, uv, node must be ok; claude/python missing are non-blocking)
  const requiredIds = ['docker', 'uv', 'node']
  const allReady = items
    .filter((item) => requiredIds.includes(item.id))
    .every((item) => item.status === 'ok')
    && items.find((i) => i.id === 'python')?.status !== 'missing'

  return { items, systemInfo, allReady }
}
