import { useTranslation } from 'react-i18next'
import { LinkedInIcon } from './icons'
import { footerCredit, footerDeco, footerIconLink, footerLink } from '../styles/appStyles'

export function SiteFooter() {
  const { t } = useTranslation('common')

  return (
    <footer className={footerDeco}>
      <div>{t('footer.line')}</div>
      <div className={footerCredit}>
        <span>
          {t('footer.createdBy')}{' '}
          <a
            className={footerLink}
            href="https://github.com/MaelBuilds"
            target="_blank"
            rel="noopener noreferrer"
          >
            @MaelBuilds
          </a>
        </span>
        <a
          className={footerIconLink}
          href="https://www.linkedin.com/in/maelpalau"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Mael Palau on LinkedIn"
        >
          <LinkedInIcon />
        </a>
      </div>
    </footer>
  )
}
