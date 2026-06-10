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

/** SVG Repo 354000 (linkedin-icon), recolored to Bookmarked palette */
const LINKEDIN_ICON_PATH =
  'M218.123122,218.127392 L180.191928,218.127392 L180.191928,158.724263 C180.191928,144.559023 179.939053,126.323993 160.463756,126.323993 C140.707926,126.323993 137.685284,141.757585 137.685284,157.692986 L137.685284,218.123441 L99.7540894,218.123441 L99.7540894,95.9665207 L136.168036,95.9665207 L136.168036,112.660562 L136.677736,112.660562 C144.102746,99.9650027 157.908637,92.3824528 172.605689,92.9280076 C211.050535,92.9280076 218.138927,118.216023 218.138927,151.114151 L218.123122,218.127392 Z M56.9550587,79.2685282 C44.7981969,79.2707099 34.9413443,69.4171797 34.9391618,57.260052 C34.93698,45.1029244 44.7902948,35.2458562 56.9471566,35.2436736 C69.1040185,35.2414916 78.9608713,45.0950217 78.963054,57.2521493 C78.9641017,63.090208 76.6459976,68.6895714 72.5186979,72.8184433 C68.3913982,76.9473153 62.7929898,79.26748 56.9550587,79.2685282 M75.9206558,218.127392 L37.94995,218.127392 L37.94995,95.9665207 L75.9206558,95.9665207 L75.9206558,218.127392 Z M237.033403,0.0182577091 L18.8895249,0.0182577091 C8.57959469,-0.0980923971 0.124827038,8.16056231 -0.001,18.4706066 L-0.001,237.524091 C0.120519052,247.839103 8.57460631,256.105934 18.8895249,255.9977 L237.033403,255.9977 C247.368728,256.125818 255.855922,247.859464 255.999,237.524091 L255.999,18.4548016 C255.851624,8.12438979 247.363742,-0.133792868 237.033403,0.000790807055'

export function LinkedInIcon() {
  return (
    <svg
      height="1em"
      width="1em"
      viewBox="0 0 256 256"
      aria-hidden
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: 'block' }}
    >
      <path fill="currentColor" d={LINKEDIN_ICON_PATH} />
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
