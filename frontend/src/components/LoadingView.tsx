import {
  loadingBox,
  loadingLabel,
  loadingStep,
  progressFill,
  progressTrack,
} from '../styles/appStyles'
import { LoadingBookSvg } from './icons'

type LoadingViewProps = {
  stepText: string
  stepOpacity: number
  progressPct: number
}

export function LoadingView({ stepText, stepOpacity, progressPct }: LoadingViewProps) {
  return (
    <div className={loadingBox}>
      <div style={{ margin: '0 auto 24px' }}>
        <LoadingBookSvg />
      </div>
      <div className={loadingLabel}>Reading your page…</div>
      <div className={loadingStep} style={{ opacity: stepOpacity }}>
        {stepText}
      </div>
      <div className={progressTrack}>
        <div className={progressFill} style={{ width: `${progressPct}%` }} />
      </div>
    </div>
  )
}
