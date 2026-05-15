import { useCallback, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { page } from './styles/appStyles'
import { SiteFooter } from './components/SiteFooter'
import { MAX_FILE_BYTES } from './constants'
import {
  BookmarkedFetchError,
  postIdentify,
  postOcr,
  postSummarize,
} from './api/bookmarked'
import type { SummaryMode } from './types'
import { setAppLocale } from './i18n'
import type { AppLocale } from './i18n/locale'
import { initialLocale, writeStoredLocale } from './i18n/locale'
import { LoadingView } from './components/LoadingView'
import { ResultView } from './components/ResultView'
import { SiteHeader } from './components/SiteHeader'
import { UploadCard } from './components/UploadCard'
import { LanguageSelector } from './components/LanguageSelector'

type Phase = 'upload' | 'loading' | 'result'

export function App() {
  const { t, i18n } = useTranslation(['flows', 'common'])
  const [locale, setLocale] = useState<AppLocale>(initialLocale)
  const [phase, setPhase] = useState<Phase>('upload')
  const [selectedMode, setSelectedMode] = useState<SummaryMode>('light')
  const [coverMode, setCoverMode] = useState(false)
  const [originalPageText, setOriginalPageText] = useState<string | null>(null)
  const [imageBase64, setImageBase64] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [uploadKey, setUploadKey] = useState(0)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [loadingStepText, setLoadingStepText] = useState('')
  const [loadingStepOpacity, setLoadingStepOpacity] = useState(1)
  const [progressPct, setProgressPct] = useState(0)
  const [bookTitle, setBookTitle] = useState('')
  const [summaryParagraphs, setSummaryParagraphs] = useState<string[]>([])
  const [dragHighlight, setDragHighlight] = useState(false)

  const stepTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const uploadCopy = useMemo(() => {
    const variant = coverMode ? 'cover' : 'default'
    return {
      headline: t(`upload.headline.${variant}`, { ns: 'flows' }),
      subline: t(`upload.subline.${variant}`, { ns: 'flows' }),
      submitLabel: t(`upload.submit.${variant}`, { ns: 'flows' }),
    }
  }, [coverMode, t, i18n.language])

  const loadingSets = useMemo(
    () => t('loading.sets', { ns: 'flows', returnObjects: true }) as string[][],
    [t, i18n.language],
  )

  const onLocaleChange = useCallback((lng: AppLocale) => {
    void setAppLocale(lng)
    writeStoredLocale(lng)
    setLocale(lng)
  }, [])

  const setStep = useCallback((index: number, set: string[], pct: number) => {
    setLoadingStepOpacity(0)
    setProgressPct(pct)
    if (stepTimerRef.current) clearTimeout(stepTimerRef.current)
    stepTimerRef.current = setTimeout(() => {
      setLoadingStepText(set[index] ?? '')
      setLoadingStepOpacity(1)
    }, 300)
  }, [])

  const showError = useCallback((msg: string) => {
    setPhase('upload')
    setProgressPct(0)
    setErrorText(msg)
  }, [])

  const resetUploadArea = useCallback((keepCoverMode: boolean) => {
    setPreviewUrl(null)
    setImageBase64(null)
    setUploadKey((k) => k + 1)
    if (!keepCoverMode) {
      setCoverMode(false)
      setOriginalPageText(null)
    }
  }, [])

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return
      if (!file.type.startsWith('image/')) {
        setErrorText(t('errors.not_image', { ns: 'common' }))
        return
      }
      if (file.size > MAX_FILE_BYTES) {
        setErrorText(t('errors.file_too_large', { ns: 'common' }))
        return
      }
      const reader = new FileReader()
      reader.onload = (ev) => {
        const dataUrl = String(ev.target?.result ?? '')
        const b64 = dataUrl.split(',')[1]
        if (!b64) {
          setErrorText(t('errors.file_read_error', { ns: 'common' }))
          return
        }
        setImageBase64(b64)
        setPreviewUrl(dataUrl)
        setErrorText(null)
      }
      reader.onerror = () => {
        setErrorText(t('errors.file_read_error', { ns: 'common' }))
      }
      reader.readAsDataURL(file)
    },
    [t],
  )

  const onSubmit = useCallback(async () => {
    if (!imageBase64) return
    setPhase('loading')
    setErrorText(null)
    setProgressPct(5)

    const set = loadingSets[Math.floor(Math.random() * loadingSets.length)]!

    try {
      setStep(0, set, 5)
      const { text: ocrText } = await postOcr(imageBase64)
      setProgressPct(33)

      const textForSummary = coverMode && originalPageText ? originalPageText : ocrText

      setStep(1, set, 38)
      const identData = await postIdentify(ocrText)
      setProgressPct(66)

      if (identData.status === 'needs_cover') {
        setPhase('upload')
        setProgressPct(0)
        if (coverMode) {
          setErrorText(t('errors.chapter_fallback', { ns: 'common' }))
        } else {
          setOriginalPageText(ocrText)
          setCoverMode(true)
          resetUploadArea(true)
        }
        return
      }

      setStep(2, set, 70)
      const { summary } = await postSummarize({
        text: textForSummary,
        book: identData.book,
        mode: selectedMode,
        ui_locale: i18n.language === 'fr' ? 'fr' : 'en',
      })

      setProgressPct(100)
      setLoadingStepText(t('loading.done', { ns: 'flows' }))
      await new Promise((r) => setTimeout(r, 500))

      setBookTitle(identData.book)
      setSummaryParagraphs(summary.split('\n\n').filter((p) => p.trim()).map((p) => p.trim()))
      setPhase('result')
      setProgressPct(0)
    } catch (err) {
      const msg =
        err instanceof BookmarkedFetchError
          ? err.message
          : t('errors.connection', { ns: 'common' })
      showError(msg)
    }
  }, [
    imageBase64,
    coverMode,
    originalPageText,
    selectedMode,
    locale,
    loadingSets,
    setStep,
    showError,
    resetUploadArea,
    t,
  ])

  const onTryAgain = useCallback(() => {
    setPhase('upload')
    setImageBase64(null)
    setPreviewUrl(null)
    setCoverMode(false)
    setOriginalPageText(null)
    setErrorText(null)
    setUploadKey((k) => k + 1)
  }, [])

  const showLanguageSelector = phase === 'upload' || phase === 'result'

  return (
    <div className={page}>
      {showLanguageSelector ? (
        <LanguageSelector value={locale} onChange={onLocaleChange} />
      ) : null}

      <SiteHeader />

      {phase === 'upload' && (
        <UploadCard
          headline={uploadCopy.headline}
          subline={uploadCopy.subline}
          submitLabel={uploadCopy.submitLabel}
          selectedMode={selectedMode}
          onModeChange={setSelectedMode}
          coverMode={coverMode}
          previewUrl={previewUrl}
          uploadKey={uploadKey}
          errorText={errorText}
          imageBase64={imageBase64}
          dragHighlight={dragHighlight}
          onDragHighlight={setDragHighlight}
          onFile={handleFile}
          onSubmit={onSubmit}
        />
      )}

      {phase === 'loading' && (
        <LoadingView
          stepText={loadingStepText}
          stepOpacity={loadingStepOpacity}
          progressPct={progressPct}
        />
      )}

      {phase === 'result' && (
        <ResultView
          bookTitle={bookTitle}
          summaryParagraphs={summaryParagraphs}
          onTryAgain={onTryAgain}
        />
      )}

      <SiteFooter />
    </div>
  )
}
