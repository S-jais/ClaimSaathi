"use client";

import React, { createContext, useContext, useSyncExternalStore } from "react";
import enDictionary from "../locales/en.json";
import hiDictionary from "../locales/hi.json";
import hinglishDictionary from "../locales/hinglish.json";
import { INSURANCE_GLOSSARY, GlossaryTerm } from "../locales/glossary";

export type SupportedLanguage = "en" | "hi" | "hinglish";

export interface LanguageOption {
  code: SupportedLanguage;
  label: string;
  nativeName: string;
  flag: string;
  desc: string;
}

export const AVAILABLE_LANGUAGES: LanguageOption[] = [
  {
    code: "en",
    label: "English",
    nativeName: "English",
    flag: "🇬🇧",
    desc: "Standard professional English",
  },
  {
    code: "hi",
    label: "Hindi",
    nativeName: "हिन्दी",
    flag: "🇮🇳",
    desc: "शुद्ध एवं प्रामाणिक देवनागरी हिन्दी",
  },
  {
    code: "hinglish",
    label: "Hinglish",
    nativeName: "Hinglish",
    flag: "🔤",
    desc: "Conversational Hindi in Roman script",
  },
];

interface LanguageContextType {
  lang: SupportedLanguage;
  setLang: (lang: SupportedLanguage) => void;
  toggleLang: () => void;
  t: (path: string, fallback?: string, params?: Record<string, string | number>) => string;
  getGlossaryTerm: (key: string) => GlossaryTerm | undefined;
  glossary: Record<string, GlossaryTerm>;
  availableLanguages: LanguageOption[];
}

const dictionaries: Record<SupportedLanguage, Record<string, unknown>> = {
  en: enDictionary as unknown as Record<string, unknown>,
  hi: hiDictionary as unknown as Record<string, unknown>,
  hinglish: hinglishDictionary as unknown as Record<string, unknown>,
};

function getLangSnapshot(): SupportedLanguage {
  if (typeof window === "undefined") return "en";
  try {
    const saved = localStorage.getItem("claimsaathi_lang");
    if (saved === "hi" || saved === "hinglish" || saved === "en") {
      return saved;
    }
  } catch {}
  return "en";
}

function getLangServerSnapshot(): SupportedLanguage {
  return "en";
}

function subscribeLang(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  window.addEventListener("claimsaathi_lang_change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("claimsaathi_lang_change", callback);
  };
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const lang = useSyncExternalStore(subscribeLang, getLangSnapshot, getLangServerSnapshot);

  const setLang = (newLang: SupportedLanguage) => {
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("claimsaathi_lang", newLang);
        document.documentElement.lang = newLang === "hi" ? "hi" : "en";
        window.dispatchEvent(new Event("claimsaathi_lang_change"));
      } catch (err) {
        console.warn("Failed to persist language:", err);
      }
    }
  };

  const toggleLang = () => {
    const next: SupportedLanguage = lang === "en" ? "hi" : lang === "hi" ? "hinglish" : "en";
    setLang(next);
  };

  const t = (path: string, fallback?: string, params?: Record<string, string | number>): string => {
    const keys = path.split(".");
    let current: unknown = dictionaries[lang] || dictionaries.en;

    for (const k of keys) {
      if (!current || typeof current !== "object") {
        current = undefined;
        break;
      }
      current = (current as Record<string, unknown>)[k];
    }

    let text: string | undefined = typeof current === "string" ? current : undefined;

    // Fall back to English dictionary if missing in target language
    if (!text && lang !== "en") {
      let enFallback: unknown = dictionaries.en;
      for (const k of keys) {
        if (!enFallback || typeof enFallback !== "object") {
          enFallback = undefined;
          break;
        }
        enFallback = (enFallback as Record<string, unknown>)[k];
      }
      if (typeof enFallback === "string") {
        text = enFallback;
      }
    }

    const output = text || fallback || path;

    // Interpolate {paramName}
    if (params) {
      return output.replace(/\{(\w+)\}/g, (match, key) => {
        return key in params ? String(params[key]) : match;
      });
    }

    return output;
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
        availableLanguages: AVAILABLE_LANGUAGES,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
