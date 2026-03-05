/**
 * @file docker-manager.ts
 * @description Docker Compose container lifecycle management
 *
 * Manages Docker containers for MySQL (primary database) and EverMemOS (optional).
 * Invokes docker compose commands via child_process.
 */

import { execFile } from 'child_process'
import { promisify } from 'util'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { tmpdir } from 'os'
import { DOCKER_COMPOSE_PATH, EVERMEMOS_COMPOSE_PATH, PORTS } from './constants'
import { getShellEnv } from './shell-env'

const execFileAsync = promisify(execFile)

// ─── Type Definitions ───────────────────────────────────────

export interface ContainerStatus {
  name: string
  state: 'running' | 'stopped' | 'not_found'
  ports: string
}

export interface DockerGroupStatus {
  id: string
  label: string
  containers: ContainerStatus[]
  composePath: string
  available: boolean
}

// ─── Docker Credential Store Fix ─────────────────────────────

/**
 * 缓存的 DOCKER_CONFIG 覆盖路径
 * null = 尚未检测, undefined = 不需要覆盖, string = 临时配置目录路径
 */
let dockerConfigOverride: string | undefined | null = null

/**
 * 检测 Docker 凭证助手是否可用。
 *
 * 常见场景：用户之前安装过 Docker Desktop，~/.docker/config.json 中配置了
 * "credsStore": "desktop"，但现在改用 Colima/Homebrew Docker，
 * docker-credential-desktop 不在 PATH 中，导致连拉取公共镜像都会失败。
 *
 * 修复方式：创建一个不含 credsStore 的临时 Docker 配置目录，
 * 通过 DOCKER_CONFIG 环境变量让 Docker 使用它。
 */
async function getDockerConfigOverride(env: Record<string, string>): Promise<string | undefined> {
  if (dockerConfigOverride !== null) return dockerConfigOverride

  const home = env.HOME || process.env.HOME || ''
  const configPath = join(home, '.docker', 'config.json')

  try {
    if (!existsSync(configPath)) {
      dockerConfigOverride = undefined
      return undefined
    }

    const config = JSON.parse(readFileSync(configPath, 'utf-8'))
    const credsStore = config.credsStore

    if (!credsStore) {
      dockerConfigOverride = undefined
      return undefined
    }

    // 检查凭证助手二进制文件是否存在
    const helperName = `docker-credential-${credsStore}`
    const execEnv = { ...env }
    const result = await execFileAsync('which', [helperName], { timeout: 5000, env: execEnv })
      .then(() => true)
      .catch(() => false)

    if (result) {
      dockerConfigOverride = undefined
      return undefined
    }

    // 凭证助手不存在 — 创建一个去掉 credsStore 的临时配置
    console.log(`[docker-manager] Credential helper "${helperName}" not found in PATH, creating sanitized Docker config`)
    const tempConfigDir = join(tmpdir(), 'narranexus-docker-config')
    mkdirSync(tempConfigDir, { recursive: true })

    const sanitizedConfig = { ...config }
    delete sanitizedConfig.credsStore
    delete sanitizedConfig.credHelpers
    writeFileSync(join(tempConfigDir, 'config.json'), JSON.stringify(sanitizedConfig, null, 2))

    dockerConfigOverride = tempConfigDir
    return tempConfigDir
  } catch (err) {
    console.warn('[docker-manager] Failed to check Docker credential config:', err)
    dockerConfigOverride = undefined
    return undefined
  }
}

/** 同步获取缓存的 DOCKER_CONFIG 覆盖路径（需要先调用过 getDockerConfigOverride） */
export function getCachedDockerConfigDir(): string | undefined {
  return dockerConfigOverride ?? undefined
}

/** 导出给 service-launcher 使用 */
export { getDockerConfigOverride }

// ─── Utility Functions ───────────────────────────────────────

/** Safe command execution (uses login shell env + common extra paths to ensure docker/colima are found) */
async function execSafe(
  cmd: string,
  args: string[],
  options: { timeout?: number } = {}
): Promise<{ stdout: string; stderr: string; success: boolean }> {
  try {
    const env = getShellEnv()
    // Ensure common tool paths are included (Homebrew, Docker Desktop)
    // These may not be in the cached shell env if tools were installed during this session
    // Docker Desktop bin MUST come first — on Intel Mac, Homebrew's /usr/local/bin/docker
    // is a CLI-only binary without compose plugin; Docker Desktop's docker has compose built in.
    const extraPaths = ['/Applications/Docker.app/Contents/Resources/bin', '/opt/homebrew/bin', '/usr/local/bin']
    const currentPath = env.PATH || ''
    const missingPaths = extraPaths.filter(p => !currentPath.includes(p))
    if (missingPaths.length > 0) {
      env.PATH = [...missingPaths, currentPath].join(':')
    }
    // 如果凭证助手不可用，使用临时配置目录
    const configOverride = await getDockerConfigOverride(env)
    if (configOverride) {
      env.DOCKER_CONFIG = configOverride
    }
    const result = await execFileAsync(cmd, args, {
      timeout: options.timeout ?? 30000,
      env
    })
    return { ...result, success: true }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    return { stdout: '', stderr: message, success: false }
  }
}

/**
 * Detect available compose command style (cached)
 *
 * - V2 plugin: docker compose (Docker Desktop or docker-compose-plugin package)
 * - V1 standalone: docker-compose (Homebrew or pip install)
 */
let composeStyle: 'v2' | 'v1' | null = null

async function detectComposeStyle(): Promise<'v2' | 'v1'> {
  if (composeStyle) return composeStyle

  const v2 = await execSafe('docker', ['compose', 'version'], { timeout: 5000 })
  if (v2.success) { composeStyle = 'v2'; return 'v2' }

  const v1 = await execSafe('docker-compose', ['version'], { timeout: 5000 })
  if (v1.success) { composeStyle = 'v1'; return 'v1' }

  // Default to V2 when neither is available, for clearer error messages
  composeStyle = 'v2'
  return 'v2'
}

/** Reset cache (need to re-detect after Docker installation) */
export function resetComposeDetection(): void {
  composeStyle = null
}

/** Get docker compose command prefix (auto-detect V1/V2) */
async function composeCmd(composePath: string): Promise<{ cmd: string; baseArgs: string[] }> {
  const style = await detectComposeStyle()
  return style === 'v1'
    ? { cmd: 'docker-compose', baseArgs: ['-f', composePath] }
    : { cmd: 'docker', baseArgs: ['compose', '-f', composePath] }
}

// ─── Docker Status Detection ─────────────────────────────────

export type DockerState = 'not_installed' | 'not_running' | 'starting' | 'healthy'

/**
 * Fine-grained Docker daemon state detection
 *
 * docker --version fail   → not_installed
 * docker info success     → healthy
 * docker info stderr 500  → starting (daemon initializing, need to wait)
 * docker info other error → not_running (daemon not started)
 */
export async function detectDockerState(): Promise<DockerState> {
  // Step 1: check if docker CLI is installed
  const versionResult = await execSafe('docker', ['--version'], { timeout: 5000 })
  if (!versionResult.success) return 'not_installed'

  // Step 2: check daemon status
  const infoResult = await execSafe('docker', ['info'], { timeout: 10000 })
  if (infoResult.success) return 'healthy'

  // Distinguish between "starting" (500 error) and "not running"
  const errMsg = infoResult.stderr.toLowerCase()
  if (errMsg.includes('500') || errMsg.includes('is the docker daemon running')) {
    // Could be either starting or not running — check if Docker Desktop/containerd process exists
    const isStarting = errMsg.includes('500')
    return isStarting ? 'starting' : 'not_running'
  }

  return 'not_running'
}

/**
 * Wait for Docker daemon to become healthy (poll detectDockerState)
 * @param maxWaitMs Maximum wait time in milliseconds (default 120s)
 * @param intervalMs Poll interval in milliseconds (default 2s)
 */
export async function waitForDockerReady(maxWaitMs = 120000, intervalMs = 2000): Promise<boolean> {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    const state = await detectDockerState()
    if (state === 'healthy') return true
    if (state === 'not_installed') return false
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return false
}

/** Check if Docker daemon is ready */
export async function isDockerReady(): Promise<boolean> {
  const result = await execSafe('docker', ['info'], { timeout: 10000 })
  return result.success
}

/**
 * Ensure Docker daemon is available.
 * Called before Dashboard "Start All" to handle daemon not running after reboot.
 *
 * macOS: Docker Desktop → Colima
 * Linux: systemctl → pkexec systemctl
 */
export async function ensureDockerDaemon(): Promise<boolean> {
  console.log('[docker-manager] ensureDockerDaemon: checking if docker is already ready...')
  if (await isDockerReady()) {
    console.log('[docker-manager] ensureDockerDaemon: docker already ready')
    return true
  }

  if (process.platform === 'darwin') {
    // Strategy 1: Launch Docker Desktop (use `open -Ra` to find it anywhere, not just /Applications)
    let dockerDesktopFound = false
    try {
      await execSafe('open', ['-Ra', 'Docker'], { timeout: 5000 })
      dockerDesktopFound = true
    } catch { /* Docker Desktop not registered with macOS */ }

    if (dockerDesktopFound) {
      console.log('[docker-manager] Strategy 1: Docker Desktop found, launching...')
      try {
        await execSafe('open', ['-a', 'Docker'], { timeout: 10000 })
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 2000))
          if (await isDockerReady()) {
            console.log(`[docker-manager] Strategy 1: Docker Desktop ready after ${(i + 1) * 2}s`)
            return true
          }
        }
        console.log('[docker-manager] Strategy 1: Docker Desktop timed out after 60s')
      } catch (err) {
        console.log(`[docker-manager] Strategy 1: Docker Desktop launch error: ${err}`)
      }
    } else {
      console.log('[docker-manager] Strategy 1: Docker Desktop not found via `open -Ra Docker`, skipping')
    }

    // Strategy 2: Start Colima (with auto-detected resource allocation)
    const os = require('os')
    const totalMemGB = Math.floor(os.totalmem() / (1024 * 1024 * 1024))
    const totalCPU = os.cpus().length
    const colimaMemory = Math.max(2, Math.min(12, Math.floor(totalMemGB / 2)))
    const colimaCPU = Math.max(2, Math.min(8, Math.floor(totalCPU / 2)))
    const colimaArgs = ['start', '--cpu', String(colimaCPU), '--memory', String(colimaMemory)]
    // Apple Silicon + macOS 13+ 使用 Virtualization.framework，无需安装 QEMU
    // Darwin 22.x = macOS 13 Ventura
    if (process.arch === 'arm64') {
      const darwinMajor = parseInt(os.release().split('.')[0], 10)
      if (darwinMajor >= 22) {
        colimaArgs.push('--vm-type', 'vz')
      }
    }
    console.log(`[docker-manager] System: ${totalMemGB}GB RAM, ${totalCPU} CPUs → Colima: ${colimaMemory}GB, ${colimaCPU} CPUs`)

    const colimaPaths = ['colima']
    if (process.arch === 'arm64') {
      colimaPaths.push('/opt/homebrew/bin/colima')
    } else {
      colimaPaths.push('/usr/local/bin/colima')
    }

    for (const colima of colimaPaths) {
      // Try as regular user first
      console.log(`[docker-manager] Strategy 2: Trying ${colima} ${colimaArgs.join(' ')}`)
      const result = await execSafe(colima, colimaArgs, { timeout: 300000 })
      if (!result.success) {
        console.log(`[docker-manager] Strategy 2: colima start failed: ${result.stderr.substring(0, 200)}`)

        // Rosetta / arch mismatch — skip privileges retry (won't help)
        if (result.stderr.includes('rosetta') || result.stderr.includes('native arch') || result.stderr.includes('lima compatibility')) {
          console.log('[docker-manager] Strategy 2: Rosetta/arch mismatch detected, skipping this colima path')
          continue
        }
      }
      if (await isDockerReady()) {
        console.log('[docker-manager] Strategy 2: docker ready after colima start')
        return true
      }

      // Colima may need sudo for VM networking — retry with privileges
      console.log(`[docker-manager] Strategy 2: Retrying colima start with admin privileges`)
      try {
        const { execFile: ef } = require('child_process')
        const { promisify: p } = require('util')
        const execAsync = p(ef)
        const script = `${colima} ${colimaArgs.join(' ')}`
        const escaped = script.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
        await execAsync('osascript', ['-e',
          `do shell script "${escaped}" with administrator privileges`
        ], { timeout: 300000, env: getShellEnv() })
        console.log('[docker-manager] Strategy 2: colima started with admin privileges')
      } catch (err) {
        console.log(`[docker-manager] Strategy 2: privileged colima start failed: ${err}`)
      }
      if (await isDockerReady()) {
        console.log('[docker-manager] Strategy 2: docker ready after privileged colima start')
        return true
      }
    }
  } else {
    // Linux strategy 1: direct systemctl
    console.log('[docker-manager] Linux Strategy 1: systemctl start docker')
    await execSafe('systemctl', ['start', 'docker'], { timeout: 30000 })
    if (await isDockerReady()) return true

    // Linux strategy 2: privileged systemctl
    console.log('[docker-manager] Linux Strategy 2: pkexec systemctl start docker')
    await execSafe('pkexec', ['systemctl', 'start', 'docker'], { timeout: 30000 })
    if (await isDockerReady()) return true
  }

  console.error('[docker-manager] ensureDockerDaemon: all strategies failed')
  return false
}

// ─── MySQL (Primary Database) ──────────────────────────────

/** Start MySQL containers */
export async function startMySQL(): Promise<{ success: boolean; output: string }> {
  // 端口已通 = MySQL 已经在跑，直接当作成功
  if (await checkPort(PORTS.MYSQL)) {
    console.log('[docker-manager] MySQL port already reachable, skipping compose up')
    return { success: true, output: 'MySQL already running' }
  }
  const { cmd, baseArgs } = await composeCmd(DOCKER_COMPOSE_PATH)
  // First pull may take a while, allow generous timeout (10 min)
  const result = await execSafe(cmd, [...baseArgs, 'up', '-d'], { timeout: 600000 })
  // 容器名冲突 = 之前的容器还在，也当作成功
  if (!result.success && result.stderr.includes('already in use')) {
    console.warn('[docker-manager] Container name conflict, treating as success')
    return { success: true, output: 'Container already exists' }
  }
  return {
    success: result.success,
    output: result.success ? result.stdout : result.stderr
  }
}

/** Stop MySQL containers */
export async function stopMySQL(): Promise<{ success: boolean; output: string }> {
  const { cmd, baseArgs } = await composeCmd(DOCKER_COMPOSE_PATH)
  const result = await execSafe(cmd, [...baseArgs, 'down'], { timeout: 30000 })
  return {
    success: result.success,
    output: result.success ? result.stdout : result.stderr
  }
}

/** Get MySQL container status */
export async function getMySQLStatus(): Promise<ContainerStatus[]> {
  return getComposeStatus(DOCKER_COMPOSE_PATH)
}

/** Check if MySQL port is reachable */
export async function isMySQLReady(): Promise<boolean> {
  return checkPort(PORTS.MYSQL)
}

// ─── EverMemOS (Optional) ──────────────────────────────

/** Check if EverMemOS configuration exists */
export function isEverMemOSAvailable(): boolean {
  return existsSync(EVERMEMOS_COMPOSE_PATH)
}

/** Start EverMemOS containers */
export async function startEverMemOS(): Promise<{ success: boolean; output: string }> {
  if (!isEverMemOSAvailable()) {
    return { success: false, output: 'EverMemOS config file not found' }
  }
  const { cmd, baseArgs } = await composeCmd(EVERMEMOS_COMPOSE_PATH)
  // EverMemOS includes MongoDB/ES/Milvus/Redis images, first pull needs generous timeout
  const result = await execSafe(cmd, [...baseArgs, 'up', '-d'], { timeout: 600000 })
  // 容器名冲突 = 之前的容器还在，也当作成功
  if (!result.success && result.stderr.includes('already in use')) {
    console.warn('[docker-manager] EverMemOS container name conflict, treating as success')
    return { success: true, output: 'Containers already exist' }
  }
  return {
    success: result.success,
    output: result.success ? result.stdout : result.stderr
  }
}

/** Stop EverMemOS containers */
export async function stopEverMemOS(): Promise<{ success: boolean; output: string }> {
  if (!isEverMemOSAvailable()) return { success: true, output: '' }
  const { cmd, baseArgs } = await composeCmd(EVERMEMOS_COMPOSE_PATH)
  const result = await execSafe(cmd, [...baseArgs, 'down'], { timeout: 30000 })
  return {
    success: result.success,
    output: result.success ? result.stdout : result.stderr
  }
}

// ─── Common Operations ───────────────────────────────────────

/** Start all Docker containers (MySQL + optional EverMemOS) */
export async function startAll(): Promise<{ mysql: boolean; evermemos: boolean }> {
  // Ensure Docker daemon is available (Colima may not be running after reboot)
  await ensureDockerDaemon()

  const mysqlResult = await startMySQL()
  let evermemosResult = { success: true }
  if (isEverMemOSAvailable()) {
    evermemosResult = await startEverMemOS()
  }
  return {
    mysql: mysqlResult.success,
    evermemos: evermemosResult.success
  }
}

/** Stop all Docker containers */
export async function stopAll(): Promise<void> {
  await Promise.all([stopMySQL(), stopEverMemOS()])
}

/** Get all Docker group statuses */
export async function getAllStatus(): Promise<DockerGroupStatus[]> {
  const groups: DockerGroupStatus[] = [
    {
      id: 'mysql',
      label: 'MySQL',
      containers: await getComposeStatus(DOCKER_COMPOSE_PATH),
      composePath: DOCKER_COMPOSE_PATH,
      available: existsSync(DOCKER_COMPOSE_PATH)
    }
  ]

  if (isEverMemOSAvailable()) {
    groups.push({
      id: 'evermemos',
      label: 'EverMemOS',
      containers: await getComposeStatus(EVERMEMOS_COMPOSE_PATH),
      composePath: EVERMEMOS_COMPOSE_PATH,
      available: true
    })
  }

  return groups
}

// ─── Internal Utilities ───────────────────────────────────────

/** Get container status for a given compose file */
async function getComposeStatus(composePath: string): Promise<ContainerStatus[]> {
  if (!existsSync(composePath)) return []

  const { cmd, baseArgs } = await composeCmd(composePath)
  const result = await execSafe(cmd, [
    ...baseArgs,
    'ps',
    '--format',
    'json'
  ])

  if (!result.success || !result.stdout.trim()) return []

  try {
    // docker compose ps --format json outputs one JSON object per line
    const lines = result.stdout.trim().split('\n')
    return lines.map((line) => {
      const data = JSON.parse(line)
      return {
        name: data.Name || data.Service || 'unknown',
        state: (data.State === 'running' ? 'running' : 'stopped') as 'running' | 'stopped',
        ports: data.Ports || ''
      }
    })
  } catch {
    return []
  }
}

/** Check if a port is reachable */
async function checkPort(port: number, host = '127.0.0.1'): Promise<boolean> {
  return new Promise((resolve) => {
    const net = require('net')
    const socket = new net.Socket()
    socket.setTimeout(2000)
    socket.on('connect', () => {
      socket.destroy()
      resolve(true)
    })
    socket.on('error', () => resolve(false))
    socket.on('timeout', () => {
      socket.destroy()
      resolve(false)
    })
    socket.connect(port, host)
  })
}
