"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const STEPS = ["height", "dob", "sex", "aim", "weight"] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    height: "",
    date_of_birth: "",
    sex: "",
    aim: "",
    weight: "",
  });

  const step = STEPS[currentStep];
  const progress = ((currentStep + 1) / STEPS.length) * 100;

  function canProceed() {
    switch (step) {
      case "height": return Number(form.height) > 50 && Number(form.height) < 300;
      case "dob": return form.date_of_birth.length > 0;
      case "sex": return form.sex === "M" || form.sex === "F";
      case "aim": return ["weight_loss", "maintain", "weight_gain"].includes(form.aim);
      case "weight": return Number(form.weight) > 20 && Number(form.weight) < 500;
    }
  }

  async function handleNext() {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api("/api/users/onboarding", {
        method: "POST",
        body: JSON.stringify({
          height: Number(form.height),
          weight: Number(form.weight),
          date_of_birth: form.date_of_birth,
          sex: form.sex,
          aim: form.aim,
        }),
      });
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-md">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-[var(--muted-foreground)] mb-2">
            <span>Шаг {currentStep + 1} из {STEPS.length}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 bg-[var(--color-sand)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-8 shadow-[var(--shadow-1)]">
          {/* Height */}
          {step === "height" && (
            <div className="space-y-4">
              <h2 className="font-display text-xl font-bold">Ваш рост</h2>
              <div className="relative">
                <input
                  type="number"
                  value={form.height}
                  onChange={(e) => setForm({ ...form, height: e.target.value })}
                  placeholder="170"
                  min={50} max={300}
                  className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] font-mono text-lg focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] text-sm">см</span>
              </div>
            </div>
          )}

          {/* Date of birth */}
          {step === "dob" && (
            <div className="space-y-4">
              <h2 className="font-display text-xl font-bold">Дата рождения</h2>
              <input
                type="date"
                value={form.date_of_birth}
                onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                max={new Date().toISOString().split("T")[0]}
                className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15"
              />
            </div>
          )}

          {/* Sex */}
          {step === "sex" && (
            <div className="space-y-4">
              <h2 className="font-display text-xl font-bold">Пол</h2>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { value: "M", label: "Мужчина" },
                  { value: "F", label: "Женщина" },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setForm({ ...form, sex: value })}
                    className={`py-4 rounded-[var(--radius-lg)] border text-center font-medium transition-all duration-150 ${
                      form.sex === value
                        ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]"
                        : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted-foreground)]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Aim */}
          {step === "aim" && (
            <div className="space-y-4">
              <h2 className="font-display text-xl font-bold">Ваша цель</h2>
              <div className="space-y-3">
                {[
                  { value: "weight_loss", label: "Сброс веса" },
                  { value: "maintain", label: "Удержание" },
                  { value: "weight_gain", label: "Набор массы" },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setForm({ ...form, aim: value })}
                    className={`w-full py-4 rounded-[var(--radius-lg)] border text-center font-medium transition-all duration-150 ${
                      form.aim === value
                        ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]"
                        : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted-foreground)]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Weight */}
          {step === "weight" && (
            <div className="space-y-4">
              <h2 className="font-display text-xl font-bold">Ваш вес</h2>
              <div className="relative">
                <input
                  type="number"
                  value={form.weight}
                  onChange={(e) => setForm({ ...form, weight: e.target.value })}
                  placeholder="70"
                  min={20} max={500}
                  className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] font-mono text-lg focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] text-sm">кг</span>
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 text-sm text-[var(--destructive)] text-center">{error}</p>
          )}

          {/* Navigation */}
          <div className="flex gap-3 mt-8">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep(currentStep - 1)}
                className="flex-1 py-3 border border-[var(--border)] text-[var(--muted)] rounded-[var(--radius)] font-medium hover:bg-[var(--color-sand)] transition-colors"
              >
                Назад
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={!canProceed() || loading}
              className="flex-1 py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 active:scale-[0.97]"
            >
              {loading ? "Сохранение..." : currentStep === STEPS.length - 1 ? "Завершить" : "Далее"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
