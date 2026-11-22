"use client";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { useI18n } from "@/i18n/I18nProvider";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  const { m } = useI18n();
  const t = m.auth.login;
  return (
    <AuthLayout
      title={t.title}
      subtitle={t.subtitle}
      alternateLink={{
        text: t.altText,
        href: "/signup",
        actionText: t.altAction,
      }}
    >
      <LoginForm />
    </AuthLayout>
  );
}
