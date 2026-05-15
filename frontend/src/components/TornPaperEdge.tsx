import { TORN_TOP_CLIP } from '../constants'
import { tornEdge } from '../styles/appStyles'

/** Torn top strip; clip-path on a real node (Panda omits clip-path on ::before in build). */
export function TornPaperEdge() {
  return <div className={tornEdge} style={{ clipPath: TORN_TOP_CLIP }} aria-hidden />
}
