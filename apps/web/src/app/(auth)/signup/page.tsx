"use client";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { useI18n } from "@/i18n/I18nProvider";
import { SignupForm } from "@/components/auth/SignupForm";

export default function SignupPage() {
  const { m } = useI18n();
  const t = m.auth.signup;
  return (
    <AuthLayout
      title={t.title}
      subtitle={t.subtitle}
      alternateLink={{
        text: t.altText,
        href: "/login",
        actionText: t.altAction,
      }}
    >
      <SignupForm />
    </AuthLayout>
  );
}
