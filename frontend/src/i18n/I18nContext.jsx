import { createContext, useContext, useEffect, useState } from 'react'
import { sk } from './sk'
import { en } from './en'

const DICTS = { sk, en }
const STORAGE_KEY = 'sindri:lang'

const I18nContext = createContext(null)

function resolve(dict, key) {
  return key.split('.').reduce((obj, part) => (obj == null ? obj : obj[part]), dict)
}

function interpolate(str, vars) {
  if (!vars) return str
  return str.replace(/\{\{(\w+)\}\}/g, (_, name) => (vars[name] != null ? vars[name] : ''))
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() =>
    localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'sk',
  )

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])

  function setLang(next) {
    setLangState(next === 'en' ? 'en' : 'sk')
  }

  function t(key, vars) {
    const raw = resolve(DICTS[lang], key) ?? resolve(DICTS.sk, key) ?? key
    return interpolate(raw, vars)
  }

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider')
  return ctx
}
