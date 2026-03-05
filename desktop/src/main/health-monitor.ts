/**
 * @file health-monitor.ts
 * @description Service health status polling monitor
 *
 * Periodically checks service port connectivity and HTTP responses,
 * notifies the Renderer process via events to update Dashboard status.
 */

import * as net from 'net'
import * as http from 'http'
import { EventEmitter } from 'events'
import { SERVICES, INFRA_SERVICES, HEALTH_CHECK_INTERVAL } from './constants'

// ─── Type Definitions ───────────────────────────────────────

export type HealthState = 'healthy' | 'unhealthy' | 'unknown'

export interface ServiceHealth {
  serviceId: string
  label: string
  state: HealthState
  port: number | null
  lastChecked: number
  message: string
}

export interface OverallHealth {
  services: ServiceHealth[]
  infrastructure: ServiceHealth[]
  mysql: HealthState
  allHealthy: boolean
}

// ─── HealthMonitor ──────────────────────────────────

export class HealthMonitor extends EventEmitter {
  private intervalId: ReturnType<typeof setInterval> | null = null
  private healthStates = new Map<string, ServiceHealth>()
  private infraStates = new Map<string, ServiceHealth>()

  constructor() {
    super()
    // Initialize all application services to unknown state
    for (const svc of SERVICES) {
      this.healthStates.set(svc.id, {
        serviceId: svc.id,
        label: svc.label,
        state: 'unknown',
        port: svc.port,
        lastChecked: 0,
        message: 'Waiting...'
      })
    }
    // Initialize all infrastructure services to unknown state
    for (const infra of INFRA_SERVICES) {
      this.infraStates.set(infra.id, {
        serviceId: infra.id,
        label: infra.label,
        state: 'unknown',
        port: infra.port,
        lastChecked: 0,
        message: 'Waiting...'
      })
    }
  }

  /** Start periodic health checks */
  start(): void {
    if (this.intervalId) return
    // Execute immediately once
    this.checkAll()
    this.intervalId = setInterval(() => this.checkAll(), HEALTH_CHECK_INTERVAL)
  }

  /** Stop periodic health checks */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
  }

  /** Get current health status for all services */
  getStatus(): OverallHealth {
    const services = Array.from(this.healthStates.values())
    const infrastructure = Array.from(this.infraStates.values())
    const mysql = this.infraStates.get('mysql')?.state ?? 'unknown'
    // allHealthy only considers app services and required infrastructure (MySQL); optional EverMemOS services are excluded
    const requiredInfraIds = new Set(INFRA_SERVICES.filter((i) => i.required).map((i) => i.id))
    const allHealthy =
      services.every((s) => s.state === 'healthy') &&
      infrastructure.filter((s) => requiredInfraIds.has(s.serviceId)).every((s) => s.state === 'healthy')
    return { services, infrastructure, mysql, allHealthy }
  }

  /** Manually trigger a full health check */
  async checkAll(): Promise<OverallHealth> {
    const checks: Promise<void>[] = []

    // Check infrastructure ports (MySQL, MongoDB, Elasticsearch, etc.)
    for (const infra of INFRA_SERVICES) {
      checks.push(this.checkInfraPortHealth(infra.id, infra.port))
    }

    // Check application services
    for (const svc of SERVICES) {
      if (svc.healthUrl) {
        checks.push(this.checkHttpHealth(svc.id, svc.healthUrl))
      } else if (svc.port) {
        checks.push(this.checkPortHealth(svc.id, svc.port))
      }
      // Services without ports (poller, job-trigger) are determined by ProcessManager status
    }

    await Promise.all(checks)
    const status = this.getStatus()
    this.emit('health-update', status)
    return status
  }

  // ─── Internal Methods ─────────────────────────────────────

  /** TCP port connectivity check (application services) */
  private async checkPortHealth(serviceId: string, port: number): Promise<void> {
    const reachable = await this.isPortReachable(port)
    this.updateHealth(this.healthStates, serviceId, reachable ? 'healthy' : 'unhealthy', port, reachable ? 'Port reachable' : 'Port unreachable')
  }

  /** TCP port connectivity check (infrastructure) */
  private async checkInfraPortHealth(serviceId: string, port: number): Promise<void> {
    const reachable = await this.isPortReachable(port)
    this.updateHealth(this.infraStates, serviceId, reachable ? 'healthy' : 'unhealthy', port, reachable ? 'Port reachable' : 'Port unreachable')
  }

  /** HTTP health check */
  private async checkHttpHealth(serviceId: string, url: string): Promise<void> {
    const healthy = await this.isHttpHealthy(url)
    const svc = SERVICES.find((s) => s.id === serviceId)
    this.updateHealth(
      this.healthStates,
      serviceId,
      healthy ? 'healthy' : 'unhealthy',
      svc?.port ?? null,
      healthy ? 'HTTP 200' : 'HTTP unreachable'
    )
  }

  /** Update health state for a specific service */
  private updateHealth(
    states: Map<string, ServiceHealth>,
    serviceId: string,
    state: HealthState,
    port: number | null,
    message: string
  ): void {
    const current = states.get(serviceId)
    if (!current) return

    const prev = current.state
    current.state = state
    current.port = port
    current.lastChecked = Date.now()
    current.message = message

    // Only emit event on state change
    if (prev !== state) {
      this.emit('service-health-change', serviceId, state, prev)
    }
  }

  /** Check if a TCP port is reachable */
  private isPortReachable(
    port: number,
    host = '127.0.0.1',
    timeout = 2000
  ): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket()
      socket.setTimeout(timeout)
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

  /** Check if HTTP URL returns 2xx */
  private isHttpHealthy(url: string, timeout = 3000): Promise<boolean> {
    return new Promise((resolve) => {
      const req = http.get(url, { timeout }, (res) => {
        const statusCode = res.statusCode ?? 0
        // Consume response data to prevent memory leak
        res.resume()
        resolve(statusCode >= 200 && statusCode < 400)
      })
      req.on('error', () => resolve(false))
      req.on('timeout', () => {
        req.destroy()
        resolve(false)
      })
    })
  }
}
