import { useCallback, useRef, useState } from 'react'
import { footerDeco, page } from './styles/appStyles'
import { MAX_FILE_BYTES } from './constants'
import { LOADING_SETS } from './constants/loadingSets'
import {
  BookmarkedFetchError,
  postIdentify,
  postOcr,
  postSummarize,
} from './api/bookmarked'
import type { SummaryMode } from './types'
import { LoadingView } from './components/LoadingView'
import { ResultView } from './components/ResultView'
import { SiteHeader } from './components/SiteHeader'
import { UploadCard } from './components/UploadCard'

type Phase = 'upload' | 'loading' | 'result'

const DEFAULT_HEADLINE = 'Where did you stop?'
const DEFAULT_SUBLINE =
  'Photograph your current page. Bookmarked reads where you left off and catches you up — nothing beyond your page.'

export function App() {
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
  const [headline, setHeadline] = useState(DEFAULT_HEADLINE)
  const [subline, setSubline] = useState(DEFAULT_SUBLINE)
  const [submitLabel, setSubmitLabel] = useState('Catch me up →')
  const [bookTitle, setBookTitle] = useState('')
  const [summaryParagraphs, setSummaryParagraphs] = useState<string[]>([])
  const [dragHighlight, setDragHighlight] = useState(false)

  const stepTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const resetUploadArea = useCallback((isCover: boolean) => {
    setPreviewUrl(null)
    setImageBase64(null)
    setUploadKey((k) => k + 1)
    if (!isCover) {
      setCoverMode(false)
      setOriginalPageText(null)
      setHeadline(DEFAULT_HEADLINE)
      setSubline(DEFAULT_SUBLINE)
      setSubmitLabel('Catch me up →')
    }
  }, [])

  const handleFile = useCallback((file: File | undefined) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setErrorText("That's not an image. Please photograph your page and upload a photo.")
      return
    }
    if (file.size > MAX_FILE_BYTES) {
      setErrorText('That photo is too large (max 5MB). Try a lower-resolution shot or compress it first.')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = String(ev.target?.result ?? '')
      const b64 = dataUrl.split(',')[1]
      if (!b64) {
        setErrorText("Couldn't read that file. Try a different photo.")
        return
      }
      setImageBase64(b64)
      setPreviewUrl(dataUrl)
      setErrorText(null)
    }
    reader.onerror = () => {
      setErrorText("Couldn't read that file. Try a different photo.")
    }
    reader.readAsDataURL(file)
  }, [])

  const onSubmit = useCallback(async () => {
    if (!imageBase64) return
    setPhase('loading')
    setErrorText(null)
    setProgressPct(5)

    const set = LOADING_SETS[Math.floor(Math.random() * LOADING_SETS.length)]!

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
          setErrorText(
            "Still couldn't identify the book. What chapter are you on? Type the title and chapter below and try again.",
          )
        } else {
          setOriginalPageText(ocrText)
          setCoverMode(true)
          setHeadline('Which book is it?')
          setSubline(
            "We couldn't identify the book from the page. Photo the cover or spine and we'll take it from there.",
          )
          setSubmitLabel('Try with cover →')
          resetUploadArea(true)
        }
        return
      }

      setStep(2, set, 70)
      const { summary } = await postSummarize({
        text: textForSummary,
        book: identData.book,
        mode: selectedMode,
      })

      setProgressPct(100)
      setLoadingStepText('Done ✦')
      await new Promise((r) => setTimeout(r, 500))

      setBookTitle(identData.book)
      setSummaryParagraphs(summary.split('\n\n').filter((p) => p.trim()).map((p) => p.trim()))
      setPhase('result')
      setProgressPct(0)
    } catch (err) {
      const msg =
        err instanceof BookmarkedFetchError
          ? err.message
          : 'Connection issue. Check your internet and try again.'
      showError(msg)
    }
  }, [imageBase64, coverMode, originalPageText, selectedMode, setStep, showError, resetUploadArea])

  const onTryAgain = useCallback(() => {
    setPhase('upload')
    setSubmitLabel('Catch me up →')
    setImageBase64(null)
    setPreviewUrl(null)
    setCoverMode(false)
    setOriginalPageText(null)
    setHeadline(DEFAULT_HEADLINE)
    setSubline(DEFAULT_SUBLINE)
    setErrorText(null)
    setUploadKey((k) => k + 1)
  }, [])

  return (
    <div className={page}>
      <SiteHeader />

      {phase === 'upload' && (
        <UploadCard
          headline={headline}
          subline={subline}
          submitLabel={submitLabel}
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

      <div className={footerDeco}>crafted for readers who wander ✦ come back often</div>
    </div>
  )
}
