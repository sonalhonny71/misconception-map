import { describe, it, expect } from 'vitest'
import { splitMathText } from './mathText'

describe('splitMathText', () => {
  it('keeps pure maths as one maths piece', () => {
    expect(splitMathText('3x + 2 = 11')).toEqual([{ type: 'math', value: '3x + 2 = 11' }])
    expect(splitMathText('ab + ac')).toEqual([{ type: 'math', value: 'ab + ac' }])
    expect(splitMathText('a(b + c) = ab + ac')).toEqual([{ type: 'math', value: 'a(b + c) = ab + ac' }])
  })

  it('keeps plain sentences as text', () => {
    expect(splitMathText('Which comparison is correct?')).toEqual([
      { type: 'text', value: 'Which comparison is correct?' },
    ])
  })

  it('splits sentences that contain maths', () => {
    expect(splitMathText('Evaluate |-15|.')).toEqual([
      { type: 'text', value: 'Evaluate' },
      { type: 'math', value: '|-15|.' },
    ])
    expect(splitMathText('Solve 3x + 2 = 11 for x')).toEqual([
      { type: 'text', value: 'Solve' },
      { type: 'math', value: '3x + 2 = 11' },
      { type: 'text', value: 'for' },
      { type: 'math', value: 'x' },
    ])
  })
})
