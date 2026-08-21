import { describe, expect, it } from 'vitest'
import { buildPartOptions } from './evParts'

const catalog = [
  { key: 'battery_pack', name: 'Battery Pack', category: 'battery', description: 'Battery', mlSupported: true, mlSignalGroup: 'battery' },
  { key: 'tires', name: 'Tires', category: 'wheels', description: 'Tires', mlSupported: true, mlSignalGroup: 'tires' },
]

describe('buildPartOptions', () => {
  it('marks active parts as already added and archived parts as restorable', () => {
    const options = buildPartOptions(catalog, [
      { name: 'Battery Pack', isActive: true },
      { name: 'Tires', isActive: false },
    ])

    expect(options).toEqual([
      expect.objectContaining({ key: 'battery_pack', availability: 'active' }),
      expect.objectContaining({ key: 'tires', availability: 'archived' }),
    ])
  })

  it('keeps missing catalog parts available', () => {
    const options = buildPartOptions(catalog, [])

    expect(options.every((option) => option.availability === 'available')).toBe(true)
  })
})
