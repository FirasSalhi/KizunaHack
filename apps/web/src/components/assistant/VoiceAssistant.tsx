"use client";

import { useEffect } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { getAssistant, type AssistantLanguage } from "./farmAssistant";

const LANGS: AssistantLanguage[] = ["fr", "en", "ar", "ja"];

/** Mounts the voice assistant bubble on every dashboard page, in the dashboard's language. */
export function VoiceAssistant() {
  const { locale } = useI18n();

  useEffect(() => {
    const assistant = getAssistant();
    assistant.attach();
    return () => assistant.detach();
  }, []);

  useEffect(() => {
    getAssistant().setLanguage(LANGS.includes(locale as AssistantLanguage) ? (locale as AssistantLanguage) : "fr");
  }, [locale]);

  return null;
}
