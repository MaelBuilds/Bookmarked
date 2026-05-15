import i18n from '../i18n'
import type { SummaryMode } from '../types'
import type { AppLocale } from '../i18n/locale'

export type IdentifyResponse =
  | { status: 'ok'; book: string }
  | { status: 'needs_cover' }

type ApiErrorBody = { code?: string; error?: string }

export class BookmarkedFetchError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BookmarkedFetchError'
  }
}

function localizedError(code: string | undefined, status: number): string {
  if (code) {
    const key = `errors.${code}`
    if (i18n.exists(key, { ns: 'common' })) {
      return i18n.t(key, { ns: 'common' })
    }
  }
  const byStatus: Record<number, string> = {
    413: 'errors.payload_too_large',
    429: 'errors.rate_limit',
    400: 'errors.bad_image',
  }
  const statusKey = byStatus[status]
  if (statusKey && i18n.exists(statusKey, { ns: 'common' })) {
    return i18n.t(statusKey, { ns: 'common' })
  }
  if (status >= 500) return i18n.t('errors.server_error', { ns: 'common' })
  return i18n.t('errors.unexpected', { ns: 'common' })
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
      i18n.t('errors.server_unreachable', { ns: 'common' }),
    )
  }

  if (!resp.ok) {
    let data: ApiErrorBody = {}
    try {
      data = (await resp.json()) as ApiErrorBody
    } catch {
      /* non-JSON body */
    }
    throw new BookmarkedFetchError(localizedError(data.code, resp.status))
  }

  return resp.json() as Promise<T>
}

export function postOcr(image: string) {
  return checkedFetch<{ text: string }>('/ocr', { image })
}

export function postIdentify(text: string) {
  return checkedFetch<IdentifyResponse>('/identify', { text })
}

export function postSummarize(args: {
  text: string
  book: string
  mode: SummaryMode
  ui_locale: AppLocale
}) {
  return checkedFetch<{ summary: string }>('/summarize', args)
}
