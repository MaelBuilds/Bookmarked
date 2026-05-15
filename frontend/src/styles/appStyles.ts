import { css } from '../../styled-system/css'

/** Shared frosted paper surface for cards + torn top edge (must stay identical). */
const cardSurface = {
  background: 'rgba(253, 246, 232, 0.88)',
  backdropFilter: 'blur(12px)',
}

export const page = css({
  position: 'relative',
  zIndex: '1',
  maxWidth: '520px',
  margin: '0 auto',
  padding: '0 20px 60px',
  minHeight: '100vh',
})

export const siteHeader = css({
  textAlign: 'center',
  padding: '64px 0 8px',
  position: 'relative',
})

export const headerDeco = css({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '14px',
  marginBottom: '6px',
})

export const headerLine = css({
  flex: '1',
  height: '1.5px',
  background: 'linear-gradient(90deg, transparent, #D4831E, transparent)',
  maxWidth: '80px',
})

export const siteTitle = css({
  fontFamily: 'display',
  fontSize: '42px',
  fontWeight: '900',
  color: 'ink',
  letterSpacing: '-0.5px',
  lineHeight: '1',
})

export const siteTitleEm = css({
  fontStyle: 'italic',
  color: 'rust',
})

export const siteTagline = css({
  fontFamily: 'accent',
  fontSize: '20px',
  color: 'ink',
  marginTop: '4px',
  letterSpacing: '0.3px',
  opacity: '0.7',
})

export const uploadCard = css({
  ...cardSurface,
  borderRadius: '4px',
  border: '1.5px solid rgba(44,26,14,0.12)',
  padding: '30px 28px 24px',
  marginTop: '28px',
  position: 'relative',
  boxShadow:
    '4px 4px 0 rgba(44,26,14,0.06), 0 8px 32px rgba(44,26,14,0.08)',
  overflow: 'visible',
})

export const tornEdge = css({
  ...cardSurface,
  position: 'absolute',
  top: '-6px',
  left: '10px',
  right: '10px',
  height: '12px',
  borderRadius: '2px',
  pointerEvents: 'none',
  zIndex: 1,
})

export const cardEyebrow = css({
  fontFamily: 'accent',
  fontSize: '15px',
  color: 'warmGrey',
  textAlign: 'center',
  marginBottom: '6px',
})

export const cardHeadline = css({
  fontFamily: 'display',
  fontSize: '26px',
  fontWeight: '700',
  color: 'ink',
  textAlign: 'center',
  lineHeight: '1.2',
  marginBottom: '8px',
})

export const cardSubline = css({
  fontSize: '13.5px',
  color: 'warmGrey',
  textAlign: 'center',
  lineHeight: '1.6',
  marginBottom: '22px',
})

export const modeSelector = css({
  display: 'flex',
  gap: '8px',
  marginBottom: '20px',
  justifyContent: 'center',
})

export const uploadAreaBase = css({
  border: '2px dashed rgba(44,26,14,0.22)',
  borderRadius: '4px',
  padding: '32px 20px',
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'background 0.2s, border-color 0.2s',
  position: 'relative',
  overflow: 'hidden',
  background: 'paper',
  _hover: {
    background: '#F7EED6',
    borderColor: 'amber',
  },
})

export const uploadAreaHasImage = css({
  padding: '0',
  borderStyle: 'solid',
  borderColor: 'rgba(44,26,14,0.15)',
})

export const previewImg = css({
  width: '100%',
  borderRadius: '2px',
  display: 'block',
  maxHeight: '300px',
  objectFit: 'cover',
})

export const uploadIconWrap = css({
  marginBottom: '10px',
  display: 'flex',
  justifyContent: 'center',
})

export const uploadLabel = css({
  fontFamily: 'display',
  fontSize: '15px',
  fontWeight: '700',
  color: 'ink',
  marginBottom: '4px',
})

export const uploadSublabel = css({
  fontFamily: 'accent',
  fontSize: '15px',
  color: 'warmGrey',
})

export const fileInput = css({
  position: 'absolute',
  inset: '0',
  opacity: '0',
  cursor: 'pointer',
})

export const errorMsg = css({
  background: '#FFF0E8',
  border: '1px solid rgba(184,67,26,0.3)',
  borderRadius: '4px',
  padding: '10px 14px',
  fontSize: '13px',
  color: 'rust',
  marginTop: '12px',
  fontFamily: 'body',
  fontStyle: 'italic',
})

export const loadingBox = css({
  textAlign: 'center',
  padding: '60px 0',
  width: '100%',
})

export const loadingLabel = css({
  fontFamily: 'display',
  fontSize: '20px',
  fontWeight: '700',
  color: 'ink',
  marginBottom: '6px',
})

export const loadingStep = css({
  fontFamily: 'accent',
  fontSize: '17px',
  color: 'warmGrey',
  marginBottom: '24px',
  minHeight: '24px',
  transition: 'opacity 0.3s',
})

export const progressTrack = css({
  width: '100%',
  height: '5px',
  background: 'rgba(44,26,14,0.1)',
  borderRadius: '99px',
  overflow: 'hidden',
})

export const progressFill = css({
  height: '100%',
  width: '0%',
  background: 'rust',
  borderRadius: '99px',
  transition: 'width 0.6s ease',
})

export const resultBox = css({ width: '100%' })

export const resultSheet = css({
  ...cardSurface,
  borderRadius: '4px',
  border: '1.5px solid rgba(44,26,14,0.12)',
  padding: '30px 28px',
  boxShadow:
    '4px 4px 0 rgba(44,26,14,0.06), 0 8px 32px rgba(44,26,14,0.08)',
  position: 'relative',
  overflow: 'visible',
})

export const bookChip = css({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  background: '#F2E8D4',
  border: '1px solid rgba(44,26,14,0.15)',
  color: 'warmGrey',
  fontFamily: 'accent',
  fontSize: '14px',
  fontWeight: '700',
  padding: '4px 12px',
  borderRadius: '3px',
  marginBottom: '14px',
})

export const resultTitle = css({
  fontFamily: 'display',
  fontSize: '22px',
  fontWeight: '700',
  fontStyle: 'italic',
  color: 'ink',
  marginBottom: '6px',
})

export const resultOrnament = css({
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  marginBottom: '18px',
})

export const ornLine = css({
  flex: '1',
  height: '1px',
  background: 'linear-gradient(90deg, #D4831E, transparent)',
})

export const ornLineRev = css({
  flex: '1',
  height: '1px',
  background: 'linear-gradient(90deg, transparent, #D4831E)',
})

export const ornLeaf = css({ color: 'forest', fontSize: '14px' })

export const summaryText = css({
  fontSize: '15px',
  lineHeight: '1.85',
  color: 'ink',
  '& p + p': { marginTop: '14px' },
})

export const footerDeco = css({
  textAlign: 'center',
  marginTop: '36px',
  fontFamily: 'accent',
  fontSize: '14px',
  color: 'rgba(44, 26, 14, 0.6)',
})
