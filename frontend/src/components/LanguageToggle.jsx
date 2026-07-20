import { useTranslation } from '../i18n/I18nContext.jsx'

export default function LanguageToggle() {
  const { lang, setLang } = useTranslation()

  return (
    <div className="flex items-center rounded border border-border-strong text-[10px] text-text-tertiary">
      <button
        type="button"
        onClick={() => setLang('sk')}
        className={`px-1.5 py-0.5 ${lang === 'sk' ? 'bg-fjord text-text-primary' : 'hover:text-text-secondary'}`}
      >
        SK
      </button>
      <button
        type="button"
        onClick={() => setLang('en')}
        className={`px-1.5 py-0.5 ${lang === 'en' ? 'bg-fjord text-text-primary' : 'hover:text-text-secondary'}`}
      >
        EN
      </button>
    </div>
  )
}
