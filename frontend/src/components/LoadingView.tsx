import { useTranslation } from 'react-i18next'
import {
  loadingBox,
  loadingLabel,
  loadingStep,
  progressFill,
  progressTrack,
} from '../styles/appStyles'

type LoadingViewProps = {
  stepText: string
  stepOpacity: number
  progressPct: number
  warmingUp?: boolean
}

export function LoadingView({ stepText, stepOpacity, progressPct, warmingUp }: LoadingViewProps) {
  const { t } = useTranslation('flows')

  const displayText = warmingUp ? t('loading.warmup') : stepText
  const displayOpacity = warmingUp ? 1 : stepOpacity

  return (
    <div className={loadingBox}>
      <div className={loadingLabel}>{t('loading.label')}</div>
      <div className={loadingStep} style={{ opacity: displayOpacity }}>
        {displayText}
      </div>
      <div className={progressTrack}>
        <div className={progressFill} style={{ width: `${progressPct}%` }} />
      </div>
    </div>
  )
}
