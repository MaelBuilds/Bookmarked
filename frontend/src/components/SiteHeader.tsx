import { useTranslation } from 'react-i18next'
import {
  headerDeco,
  headerLine,
  siteHeader,
  siteTagline,
  siteTitle,
  siteTitleEm,
} from '../styles/appStyles'
import { HeaderBookmarkSvg } from './icons'

export function SiteHeader() {
  const { t } = useTranslation('common')

  return (
    <header className={siteHeader}>
      <div className={headerDeco}>
        <div className={headerLine} />
        <HeaderBookmarkSvg />
        <div className={headerLine} />
      </div>
      <h1 className={siteTitle}>
        Book<span className={siteTitleEm}>marked</span>
      </h1>
      <p className={siteTagline}>{t('tagline')}</p>
    </header>
  )
}
