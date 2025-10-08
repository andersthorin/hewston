import '@testing-library/jest-dom'
import { afterEach, beforeEach, vi } from 'vitest'

// Focused strictness: fail tests only on React act() warnings.
let __consoleErrors: string[] = []
let __consoleWarnings: string[] = []

const origError = console.error.bind(console)
const origWarn = console.warn.bind(console)

beforeEach(() => {
  __consoleErrors = []
  __consoleWarnings = []
  vi.spyOn(console, 'error').mockImplementation((...args: any[]) => {
    const msg = args.map(String).join(' ')
    __consoleErrors.push(msg)
    origError(...args)
  })
  vi.spyOn(console, 'warn').mockImplementation((...args: any[]) => {
    const msg = args.map(String).join(' ')
    __consoleWarnings.push(msg)
    origWarn(...args)
  })
})

afterEach(() => {
  const all = [...__consoleErrors, ...__consoleWarnings]
  vi.restoreAllMocks()
  const actIssues = all.filter((m) => m.toLowerCase().includes('not wrapped in act'))
  if (actIssues.length) {
    throw new Error(`React act() warning(s) occurred during test:\n${actIssues.join('\n')}`)
  }
})
