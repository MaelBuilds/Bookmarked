import type { SummaryMode } from '../types'

export type IdentifyResponse =
  | { status: 'ok'; book: string }
  | { status: 'needs_cover' }

export class BookmarkedFetchError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BookmarkedFetchError'
  }
}

export async function checkedFetch<T>(url: string, body: unknown): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new BookmarkedFetchError(
      'Cannot reach the server. Start Flask (python server.py) and keep it running on port 3000.',
    )
  }
  if (resp.status === 413) {
    throw new BookmarkedFetchError('That photo is too large. Try a lower-resolution shot.')
  }
  if (resp.status === 429) {
    throw new BookmarkedFetchError("You've hit the daily limit. Try again tomorrow.")
  }
  if (resp.status === 400) {
    throw new BookmarkedFetchError("Couldn't read the image. Try a clearer photo.")
  }
  if (resp.status >= 500) {
    throw new BookmarkedFetchError('Server error. Try again in a moment.')
  }
  if (!resp.ok) {
    throw new BookmarkedFetchError('Something unexpected happened. Try again.')
  }
  return resp.json() as Promise<T>
}

export function postOcr(image: string) {
  return checkedFetch<{ text: string }>('/ocr', { image })
}

export function postIdentify(text: string) {
  return checkedFetch<IdentifyResponse>('/identify', { text })
}

export function postSummarize(args: { text: string; book: string; mode: SummaryMode }) {
  return checkedFetch<{ summary: string }>('/summarize', args)
}
