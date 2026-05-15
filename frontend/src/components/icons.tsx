export function HeaderBookmarkSvg() {
  return (
    <svg width="22" height="30" viewBox="0 0 22 30" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M2 2 H20 V28 L11 22 L2 28 Z"
        fill="#B8431A"
        stroke="#7A2E1A"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <line x1="6" y1="8" x2="16" y2="8" stroke="#FDF6E8" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="6" y1="12" x2="14" y2="12" stroke="#FDF6E8" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

export function OpenBookSvg() {
  return (
    <svg width="56" height="44" viewBox="0 0 56 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M28 38 C28 38 14 32 4 34 L4 8 C14 6 28 12 28 12"
        stroke="#7A2E1A"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M28 38 C28 38 42 32 52 34 L52 8 C42 6 28 12 28 12"
        stroke="#7A2E1A"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      <path d="M28 12 L28 38" stroke="#C9963A" strokeWidth="1.5" strokeDasharray="3,2" />
      <line x1="10" y1="16" x2="24" y2="14" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      <line x1="10" y1="21" x2="24" y2="19" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
      <line x1="10" y1="26" x2="22" y2="24" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.4" />
      <line x1="32" y1="14" x2="46" y2="16" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      <line x1="32" y1="19" x2="46" y2="21" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
      <line x1="34" y1="24" x2="46" y2="26" stroke="#B8431A" strokeWidth="1" strokeLinecap="round" opacity="0.4" />
    </svg>
  )
}

export function CoverPromptSvg() {
  return (
    <svg width="50" height="50" viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="4" width="30" height="42" rx="3" fill="#F5E8CC" stroke="#7A2E1A" strokeWidth="2" />
      <rect x="8" y="4" width="8" height="42" rx="2" fill="#C9963A" stroke="#7A2E1A" strokeWidth="1.5" />
      <line x1="20" y1="16" x2="34" y2="16" stroke="#7A2E1A" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="20" y1="22" x2="34" y2="22" stroke="#7A2E1A" strokeWidth="1" strokeLinecap="round" />
      <line x1="20" y1="28" x2="30" y2="28" stroke="#7A2E1A" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

export function LoadingBookSvg() {
  return (
    <svg width="80" height="64" viewBox="0 0 80 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <style>
        {`
          .page-flip { transform-origin: 40px 32px; animation: flip 1.8s ease-in-out infinite; }
          .page-flip-2 { transform-origin: 40px 32px; animation: flip 1.8s ease-in-out infinite 0.3s; opacity: 0.6; }
          @keyframes flip {
            0%, 100% { transform: scaleX(1); }
            40% { transform: scaleX(0.05); }
            60% { transform: scaleX(0.05); }
          }
          .leaf-fall { animation: fall 2.4s ease-in infinite; }
          .leaf-fall-2 { animation: fall 2.4s ease-in infinite 0.8s; }
          @keyframes fall {
            0% { transform: translateY(0) rotate(0deg); opacity: 1; }
            100% { transform: translateY(40px) rotate(45deg); opacity: 0; }
          }
        `}
      </style>
      <path
        d="M40 56 C40 56 18 48 6 50 L6 12 C18 10 40 18 40 18"
        stroke="#7A2E1A"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M40 56 C40 56 62 48 74 50 L74 12 C62 10 40 18 40 18"
        stroke="#7A2E1A"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      <rect className="page-flip" x="28" y="18" width="12" height="38" rx="1" fill="#F5E8CC" opacity="0.9" />
      <rect className="page-flip-2" x="28" y="18" width="10" height="38" rx="1" fill="#F5E8CC" opacity="0.6" />
      <path d="M40 18 L40 56" stroke="#C9963A" strokeWidth="1.5" strokeDasharray="3,2" />
      <g className="leaf-fall" transform="translate(20, 0)">
        <path
          d="M55 4 C52 10 46 11 44 9 C45 14 43 18 40 20 C43 20 46 23 46 27 C48 24 51 23 53 26 C53 22 56 20 59 21 C57 18 56 14 57 10 C55 12 51 12 50 9 C53 9 55 4 55 4Z"
          fill="#B8431A"
          opacity="0.8"
        />
      </g>
      <g className="leaf-fall-2" transform="translate(0, 0)">
        <path
          d="M18 8 C16 13 11 14 9 12 C10 17 8 21 5 22 C8 23 10 26 10 30 C12 27 15 26 17 28 C17 24 20 22 22 23 C20 20 20 16 21 12 C19 14 15 14 14 11 C16 11 18 8 18 8Z"
          fill="#D4831E"
          opacity="0.7"
        />
      </g>
    </svg>
  )
}
