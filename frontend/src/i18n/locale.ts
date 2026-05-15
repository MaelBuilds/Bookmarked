export type AppLocale = 'en' | 'fr'

export const LOCALE_STORAGE_KEY = 'bookmarked.locale'
export const SUPPORTED_LOCALES: AppLocale[] = ['en', 'fr']

export function browserDefaultLocale(): AppLocale {
  const lang = typeof navigator !== 'undefined' ? navigator.language : 'en'
  return lang.toLowerCase().startsWith('fr') ? 'fr' : 'en'
}

export function readStoredLocale(): AppLocale | null {
  try {
    const raw = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (raw === 'en' || raw === 'fr') return raw
  } catch {
    /* private mode / blocked storage */
  }
  return null
}

export function writeStoredLocale(locale: AppLocale) {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    /* ignore */
  }
}

export function initialLocale(): AppLocale {
  return readStoredLocale() ?? browserDefaultLocale()
}

export function applyDocumentLang(locale: AppLocale) {
  document.documentElement.lang = locale
}
