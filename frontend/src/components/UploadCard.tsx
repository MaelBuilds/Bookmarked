import { modePill, btnPrimary } from '../../styled-system/recipes'
import type { SummaryMode } from '../types'
import {
  cardEyebrow,
  cardHeadline,
  cardSubline,
  errorMsg,
  fileInput,
  modeSelector,
  previewImg,
  uploadAreaBase,
  uploadAreaHasImage,
  uploadCard,
  uploadIconWrap,
  uploadLabel,
  uploadSublabel,
} from '../styles/appStyles'
import { CoverPromptSvg, OpenBookSvg } from './icons'

type UploadCardProps = {
  headline: string
  subline: string
  submitLabel: string
  selectedMode: SummaryMode
  onModeChange: (mode: SummaryMode) => void
  coverMode: boolean
  previewUrl: string | null
  uploadKey: number
  errorText: string | null
  imageBase64: string | null
  dragHighlight: boolean
  onDragHighlight: (on: boolean) => void
  onFile: (file: File | undefined) => void
  onSubmit: () => void
}

export function UploadCard({
  headline,
  subline,
  submitLabel,
  selectedMode,
  onModeChange,
  coverMode,
  previewUrl,
  uploadKey,
  errorText,
  imageBase64,
  dragHighlight,
  onDragHighlight,
  onFile,
  onSubmit,
}: UploadCardProps) {
  const uploadAreaClass =
    previewUrl != null ? `${uploadAreaBase} ${uploadAreaHasImage}` : uploadAreaBase

  return (
    <div className={`${uploadCard} card-torn-top`}>
      <p className={cardEyebrow}>✦ no spoilers, ever ✦</p>
      <h2 className={cardHeadline}>{headline}</h2>
      <p className={cardSubline}>{subline}</p>

      <div className={modeSelector}>
        <button
          type="button"
          className={modePill({ active: selectedMode === 'light' })}
          onClick={() => onModeChange('light')}
        >
          ✦ Previously on…
        </button>
        <button
          type="button"
          className={modePill({ active: selectedMode === 'full' })}
          onClick={() => onModeChange('full')}
        >
          Full recap
        </button>
      </div>

      <div
        className={uploadAreaClass}
        style={
          dragHighlight && !previewUrl
            ? { background: '#F7EED6', borderColor: '#D4831E' }
            : undefined
        }
        onDragOver={(e) => {
          e.preventDefault()
          if (!previewUrl) onDragHighlight(true)
        }}
        onDragLeave={() => onDragHighlight(false)}
        onDrop={(e) => {
          e.preventDefault()
          onDragHighlight(false)
          onFile(e.dataTransfer.files[0])
        }}
      >
        {previewUrl ? (
          <img className={previewImg} src={previewUrl} alt="Page preview" />
        ) : coverMode ? (
          <>
            <div className={uploadIconWrap}>
              <CoverPromptSvg />
            </div>
            <div className={uploadLabel}>Photograph the cover or spine</div>
            <div className={uploadSublabel}>We&apos;ll use it to identify your book</div>
          </>
        ) : (
          <>
            <div className={uploadIconWrap}>
              <OpenBookSvg />
            </div>
            <div className={uploadLabel}>Photograph your current page</div>
            <div className={uploadSublabel}>or drop an image here</div>
          </>
        )}
        <input
          key={uploadKey}
          className={fileInput}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
      </div>

      {errorText ? <div className={errorMsg}>{errorText}</div> : null}

      <button
        type="button"
        className={btnPrimary()}
        disabled={!imageBase64}
        onClick={onSubmit}
      >
        {submitLabel}
      </button>
    </div>
  )
}
