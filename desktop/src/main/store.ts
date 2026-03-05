/**
 * @file store.ts
 * @description Simple JSON persistent storage, replacing electron-store to avoid ESM compatibility issues
 */

import { app } from 'electron'
import { join } from 'path'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'

interface StoreData {
  setupComplete: boolean
  [key: string]: unknown
}

const DEFAULTS: StoreData = {
  setupComplete: false
}

class SimpleStore {
  private filePath: string
  private data: StoreData

  constructor() {
    const userDataPath = app.getPath('userData')
    mkdirSync(userDataPath, { recursive: true })
    this.filePath = join(userDataPath, 'config.json')
    this.data = this.load()
  }

  get<K extends keyof StoreData>(key: K): StoreData[K] {
    return this.data[key]
  }

  set<K extends keyof StoreData>(key: K, value: StoreData[K]): void {
    this.data[key] = value
    this.save()
  }

  private load(): StoreData {
    try {
      if (existsSync(this.filePath)) {
        const raw = readFileSync(this.filePath, 'utf-8')
        return { ...DEFAULTS, ...JSON.parse(raw) }
      }
    } catch {
      // Use defaults when file is corrupted
    }
    return { ...DEFAULTS }
  }

  private save(): void {
    writeFileSync(this.filePath, JSON.stringify(this.data, null, 2), 'utf-8')
  }
}

export const store = new SimpleStore()
