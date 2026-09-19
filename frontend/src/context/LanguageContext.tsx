"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import enDictionary from "../locales/en.json";
import hiDictionary from "../locales/hi.json";
import { INSURANCE_GLOSSARY, GlossaryTerm } from "../locales/glossary";

export type SupportedLanguage = "en" | "hi";

interface LanguageContextType {
  lang: SupportedLanguage;
  setLang: (lang: SupportedLanguage) => void;
  toggleLang: () => void;
  t: (path: string, fallback?: string) => string;
  getGlossaryTerm: (key: string) => GlossaryTerm | undefined;
  glossary: Record<string, GlossaryTerm>;
}

const dictionaries: Record<SupportedLanguage, Record<string, unknown>> = {
  en: enDictionary as unknown as Record<string, unknown>,
  hi: hiDictionary as unknown as Record<string, unknown>,
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<SupportedLanguage>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("claimsaathi_lang") as SupportedLanguage | null;
      if (saved === "en" || saved === "hi") {
        return saved;
      }
    }
    return "en";
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  const setLang = (newLang: SupportedLanguage) => {
    setLangState(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("claimsaathi_lang", newLang);
      document.documentElement.lang = newLang;
    }
  };

  const toggleLang = () => {
    const next = lang === "en" ? "hi" : "en";
    setLang(next);
  };

  const t = (path: string, fallback?: string): string => {
    const keys = path.split(".");
    let current: unknown = dictionaries[lang];

    for (const k of keys) {
      if (!current || typeof current !== "object") {
        current = undefined;
        break;
      }
      current = (current as Record<string, unknown>)[k];
    }

    if (typeof current === "string") return current;

    if (lang !== "en") {
      let enFallback: unknown = dictionaries.en;
      for (const k of keys) {
        if (!enFallback || typeof enFallback !== "object") {
          enFallback = undefined;
          break;
        }
        enFallback = (enFallback as Record<string, unknown>)[k];
      }
      if (typeof enFallback === "string") return enFallback;
    }

    return fallback || path;
  };

  const getGlossaryTerm = (key: string) => {
    return INSURANCE_GLOSSARY[key];
  };

  return (
    <LanguageContext.Provider
      value={{
        lang,
        setLang,
        toggleLang,
        t,
        getGlossaryTerm,
        glossary: INSURANCE_GLOSSARY,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    // Provide safe default if outside provider
    return {
      lang: "en" as SupportedLanguage,
      setLang: () => {},
      toggleLang: () => {},
      t: (_p: string, fb?: string) => fb || _p,
      getGlossaryTerm: () => undefined,
      glossary: INSURANCE_GLOSSARY,
    };
  }
  return context;
}
