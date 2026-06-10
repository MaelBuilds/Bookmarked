import { useCallback, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { page } from './styles/appStyles'
import { SiteFooter } from './components/SiteFooter'
import { PrepareImageError, prepareUploadImage } from './lib/prepareUploadImage'
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
  const [manualBook, setManualBook] = useState('')
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
  const [warmingUp, setWarmingUp] = useState(false)

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
    async (file: File | undefined) => {
      if (!file) return
      try {
        const { dataUrl } = await prepareUploadImage(file)
        const b64 = dataUrl.split(',')[1]
        if (!b64) {
          setErrorText(t('errors.file_read_error', { ns: 'common' }))
          return
        }
        setImageBase64(b64)
        setPreviewUrl(dataUrl)
        setErrorText(null)
      } catch (err) {
        if (err instanceof PrepareImageError) {
          setErrorText(t(`errors.${err.code}`, { ns: 'common' }))
          return
        }
        setErrorText(t('errors.file_read_error', { ns: 'common' }))
      }
    },
    [t],
  )

  const onSubmit = useCallback(async () => {
    if (!imageBase64) return
    setPhase('loading')
    setErrorText(null)
    setProgressPct(5)
    setWarmingUp(false)

    const set = loadingSets[Math.floor(Math.random() * loadingSets.length)]!
    const warmupTimer = setTimeout(() => setWarmingUp(true), 4000)

    try {
      setStep(0, set, 5)
      const { text: ocrText } = await postOcr(imageBase64)
      clearTimeout(warmupTimer)
      setWarmingUp(false)
      setProgressPct(33)

      const textForSummary = coverMode && originalPageText ? originalPageText : ocrText

      setStep(1, set, 38)
      const identData = await postIdentify(ocrText)
      setProgressPct(66)

      if (identData.status === 'needs_cover') {
        setPhase('upload')
        setProgressPct(0)
        if (coverMode) {
          setErrorText(t('errors.cover_not_identified', { ns: 'common' }))
          resetUploadArea(true)
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
      clearTimeout(warmupTimer)
      setWarmingUp(false)
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

  const onManualSubmit = useCallback(async () => {
    const book = manualBook.trim()
    const textForSummary = originalPageText
    if (!book || !textForSummary) return
    setPhase('loading')
    setErrorText(null)
    setProgressPct(70)
    const set = loadingSets[Math.floor(Math.random() * loadingSets.length)]!
    try {
      setStep(2, set, 75)
      const { summary } = await postSummarize({
        text: textForSummary,
        book,
        mode: selectedMode,
        ui_locale: i18n.language === 'fr' ? 'fr' : 'en',
      })

      setProgressPct(100)
      setLoadingStepText(t('loading.done', { ns: 'flows' }))
      await new Promise((r) => setTimeout(r, 500))

      setBookTitle(book)
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
  }, [manualBook, originalPageText, selectedMode, i18n.language, loadingSets, setStep, showError, t])

  const onTryAgain = useCallback(() => {
    setPhase('upload')
    setImageBase64(null)
    setPreviewUrl(null)
    setCoverMode(false)
    setManualBook('')
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
          manualBook={manualBook}
          onManualBookChange={setManualBook}
          onManualSubmit={onManualSubmit}
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
          warmingUp={warmingUp}
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
