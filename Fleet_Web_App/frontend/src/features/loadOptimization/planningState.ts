import type { CandidateGenerationStatus } from './types'

export function generationAction(status: CandidateGenerationStatus) {
  if (status === 'failed' || status === 'cancelled') {
    return { enabled: true, label: 'Retry generation' }
  }
  if (status === 'not_started') {
    return { enabled: true, label: 'Generate candidates' }
  }
  const label = status === 'queued'
    ? 'Generation queued'
    : status === 'running'
      ? 'Generating candidates'
      : status === 'approved'
        ? 'Candidate approved'
        : 'Candidates generated'
  return { enabled: false, label }
}
