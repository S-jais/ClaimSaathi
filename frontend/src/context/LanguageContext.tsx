"use client";

import React, { createContext, useContext, useSyncExternalStore } from "react";
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

function getLangSnapshot(): SupportedLanguage {
  if (typeof window === "undefined") return "en";
  const saved = localStorage.getItem("claimsaathi_lang");
  return saved === "hi" ? "hi" : "en";
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
      localStorage.setItem("claimsaathi_lang", newLang);
      document.documentElement.lang = newLang;
      window.dispatchEvent(new Event("claimsaathi_lang_change"));
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

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
