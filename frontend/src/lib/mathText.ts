/**
 * Question text mixes plain sentences with maths, e.g.
 *   "Which comparison is correct?"           (all words)
 *   "Solve 3x + 2 = 11"                       (word + maths)
 *   "Distributive property: a(b + c) = ab + ac"
 * KaTeX treats everything as maths and drops the spaces between words, so the
 * text is first split into plain-text pieces and maths pieces.
 */
export type Segment = { type: 'text' | 'math'; value: string }

// A "word": letters (and apostrophes) with optional trailing punctuation
const WORD = /^[A-Za-z][A-Za-z']*[.,;:?!]*$/

// Short English words that are clearly words even when they stand alone
const COMMON_WORDS = new Set(['for', 'is', 'the', 'of', 'to', 'by', 'in', 'and', 'or', 'if', 'than', 'then', 'are', 'as', 'at', 'on', 'per', 'an', 'be', 'it', 'no', 'not', 'one', 'two', 'has', 'her', 'his', 'its', 'but', 'any', 'all', 'each', 'when', 'with', 'both', 'sides'])

function letterCount(token: string): number {
  return token.replace(/[^A-Za-z]/g, '').length
}

export function splitMathText(input: string): Segment[] {
  const tokens = input.split(/\s+/).filter(Boolean)
  const isWord = tokens.map((t) => WORD.test(t) && letterCount(t) >= 2)

  // A lone short "word" such as "ab" or "ac" is far more likely to be algebra than English
  let i = 0
  while (i < tokens.length) {
    if (!isWord[i]) {
      i++
      continue
    }
    let j = i
    while (j < tokens.length && isWord[j]) j++
    if (
      j - i === 1 &&
      letterCount(tokens[i]) < 4 &&
      !COMMON_WORDS.has(tokens[i].toLowerCase().replace(/[^a-z]/g, ''))
    ) {
      isWord[i] = false
    }
    i = j
  }

  const segments: Segment[] = []
  tokens.forEach((token, index) => {
    const type = isWord[index] ? 'text' : 'math'
    const last = segments[segments.length - 1]
    if (last && last.type === type) {
      last.value += ' ' + token
    } else {
      segments.push({ type, value: token })
    }
  })
  return segments
}
