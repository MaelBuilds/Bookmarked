import { btnGhost } from '../../styled-system/recipes'
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
import { TornPaperEdge } from './TornPaperEdge'

type ResultViewProps = {
  bookTitle: string
  summaryParagraphs: string[]
  onTryAgain: () => void
}

export function ResultView({ bookTitle, summaryParagraphs, onTryAgain }: ResultViewProps) {
  return (
    <div className={resultBox}>
      <div className={resultSheet}>
        <TornPaperEdge />
        <div className={bookChip}>
          📔 <span>{bookTitle}</span>
        </div>
        <div className={resultTitle}>Here&apos;s where you left off</div>
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
      <button type="button" className={btnGhost()} onClick={onTryAgain}>
        ← Try another page
      </button>
    </div>
  )
}
