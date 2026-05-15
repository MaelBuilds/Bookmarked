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
}

export function LoadingView({ stepText, stepOpacity, progressPct }: LoadingViewProps) {
  const { t } = useTranslation('flows')

  return (
    <div className={loadingBox}>
      <div className={loadingLabel}>{t('loading.label')}</div>
      <div className={loadingStep} style={{ opacity: stepOpacity }}>
        {stepText}
      </div>
      <div className={progressTrack}>
        <div className={progressFill} style={{ width: `${progressPct}%` }} />
      </div>
    </div>
  )
}
