import { describe, expect, it } from 'vitest'
import { generationAction } from './planningState'

describe('generationAction', () => {
  it.each([
    ['not_started', true, 'Generate candidates'],
    ['failed', true, 'Retry generation'],
    ['cancelled', true, 'Retry generation'],
    ['queued', false, 'Generation queued'],
    ['running', false, 'Generating candidates'],
    ['ready', false, 'Candidates generated'],
    ['approved', false, 'Candidate approved'],
  ] as const)('maps %s to a controlled action', (status, enabled, label) => {
    expect(generationAction(status)).toEqual({ enabled, label })
  })
})
