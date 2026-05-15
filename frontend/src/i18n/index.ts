import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import enCommon from '../locales/en/common.json'
import enFlows from '../locales/en/flows.json'
import frCommon from '../locales/fr/common.json'
import frFlows from '../locales/fr/flows.json'
import { applyDocumentLang, initialLocale, type AppLocale } from './locale'

const startLocale = initialLocale()
applyDocumentLang(startLocale)

void i18n.use(initReactI18next).init({
  lng: startLocale,
  fallbackLng: 'en',
  supportedLngs: ['en', 'fr'],
  ns: ['common', 'flows'],
  defaultNS: 'common',
  resources: {
    en: { common: enCommon, flows: enFlows },
    fr: { common: frCommon, flows: frFlows },
  },
  interpolation: { escapeValue: false },
})

export function setAppLocale(locale: AppLocale) {
  applyDocumentLang(locale)
  return i18n.changeLanguage(locale)
}

export default i18n
