import { useTranslation } from 'react-i18next'
import { btnTryAgain } from '../../styled-system/recipes'
import {
  bookChip,
  ornLeaf,
  ornLine,
  ornLineRev,
  resultBox,
  resultOrnament,
  resultSheet,
  resultTitle,
  summaryText,
} from '../styles/appStyles'

type ResultViewProps = {
  bookTitle: string
  summaryParagraphs: string[]
  onTryAgain: () => void
}

export function ResultView({ bookTitle, summaryParagraphs, onTryAgain }: ResultViewProps) {
  const { t } = useTranslation('flows')

  return (
    <div className={resultBox}>
      <div className={`${resultSheet} card-torn-top`}>
        <div className={bookChip}>
          📔 <span>{bookTitle}</span>
        </div>
        <div className={resultTitle}>{t('result.title')}</div>
        <div className={resultOrnament}>
          <div className={ornLine} />
          <span className={ornLeaf}>🍂</span>
          <div className={ornLineRev} />
        </div>
        <div className={summaryText}>
          {summaryParagraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </div>
      <button type="button" className={btnTryAgain()} onClick={onTryAgain}>
        {t('result.tryAgain')}
      </button>
    </div>
  )
}
