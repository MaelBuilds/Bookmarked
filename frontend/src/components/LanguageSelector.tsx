import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { AppLocale } from '../i18n/locale'
import {
  langMenu,
  langMenuItem,
  langMenuItemActive,
  langSelectorRoot,
  langTrigger,
} from '../styles/appStyles'

const OPTIONS: { value: AppLocale; emoji: string; code: string }[] = [
  { value: 'en', emoji: '☕', code: 'EN' },
  { value: 'fr', emoji: '🥐', code: 'FR' },
]

type LanguageSelectorProps = {
  value: AppLocale
  onChange: (lng: AppLocale) => void
}

function labelFor(value: AppLocale) {
  const opt = OPTIONS.find((o) => o.value === value)!
  return `${opt.emoji} ${opt.code}`
}

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const { t } = useTranslation('common')
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  const ariaFor = (lng: AppLocale) =>
    lng === 'fr' ? t('language.optionFr') : t('language.optionEn')

  return (
    <div ref={rootRef} className={langSelectorRoot}>
      <button
        type="button"
        className={langTrigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${t('language.ariaLabel')}, ${ariaFor(value)}`}
        onClick={() => setOpen((o) => !o)}
      >
        {labelFor(value)} <span aria-hidden="true">▾</span>
      </button>
      {open ? (
        <ul className={langMenu} role="listbox" aria-label={t('language.ariaLabel')}>
          {OPTIONS.map((opt) => {
            const selected = opt.value === value
            return (
              <li key={opt.value} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  aria-label={ariaFor(opt.value)}
                  className={selected ? `${langMenuItem} ${langMenuItemActive}` : langMenuItem}
                  onClick={() => {
                    onChange(opt.value)
                    setOpen(false)
                  }}
                >
                  {opt.emoji} {opt.code}
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}
