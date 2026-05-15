import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('flows')
  const uploadAreaClass =
    previewUrl != null ? `${uploadAreaBase} ${uploadAreaHasImage}` : uploadAreaBase

  return (
    <div className={`${uploadCard} card-torn-top`}>
      <p className={cardEyebrow}>{t('upload.eyebrow')}</p>
      <h2 className={cardHeadline}>{headline}</h2>
      <p className={cardSubline}>{subline}</p>

      <div className={modeSelector}>
        <button
          type="button"
          className={modePill({ active: selectedMode === 'light' })}
          onClick={() => onModeChange('light')}
        >
          {t('upload.mode.light')}
        </button>
        <button
          type="button"
          className={modePill({ active: selectedMode === 'full' })}
          onClick={() => onModeChange('full')}
        >
          {t('upload.mode.full')}
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
          <img className={previewImg} src={previewUrl} alt={t('upload.previewAlt')} />
        ) : coverMode ? (
          <>
            <div className={uploadIconWrap}>
              <CoverPromptSvg />
            </div>
            <div className={uploadLabel}>{t('upload.label.cover')}</div>
            <div className={uploadSublabel}>{t('upload.sublabel.cover')}</div>
          </>
        ) : (
          <>
            <div className={uploadIconWrap}>
              <OpenBookSvg />
            </div>
            <div className={uploadLabel}>{t('upload.label.page')}</div>
            <div className={uploadSublabel}>{t('upload.sublabel.page')}</div>
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
