"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Coffee, UtensilsCrossed, Moon, Loader2 } from "lucide-react";

type MealType = "breakfast" | "lunch" | "dinner";

interface RecipeResponse {
  recipe: string;
  meal_type?: MealType;
}

const MEALS: { type: MealType; label: string; icon: typeof Coffee }[] = [
  { type: "breakfast", label: "Завтрак", icon: Coffee },
  { type: "lunch", label: "Обед", icon: UtensilsCrossed },
  { type: "dinner", label: "Ужин", icon: Moon },
];

export default function RecipesPage() {
  const [recipe, setRecipe] = useState<string | null>(null);
  const [activeMeal, setActiveMeal] = useState<MealType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchRecipe(mealType: MealType) {
    setError(null);
    setActiveMeal(mealType);
    setLoading(true);
    try {
      const data = await api<RecipeResponse>("/api/ai/recipe", {
        method: "POST",
        body: JSON.stringify({ meal_type: mealType }),
      });
      setRecipe(data.recipe ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка запроса");
      setRecipe(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">Рецепты</h1>
        <p className="text-sm text-[var(--muted)] mt-1">Идеи блюд от AI под приём пищи</p>
      </div>

      {error && (
        <div
          className="rounded-[var(--radius-lg)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-4 py-3 text-sm"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {MEALS.map(({ type, label, icon: Icon }) => (
          <button
            key={type}
            type="button"
            onClick={() => void fetchRecipe(type)}
            disabled={loading}
            className={`inline-flex items-center gap-2 px-5 py-3 rounded-[var(--radius-lg)] border text-sm font-medium transition-all shadow-[var(--shadow-1)] ${
              activeMeal === type && loading
                ? "border-[var(--accent)] bg-[var(--card)] text-[var(--accent)]"
                : activeMeal === type && recipe != null
                  ? "border-[var(--accent)] bg-[var(--color-sand)] text-[var(--foreground)]"
                  : "border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[var(--accent)] hover:shadow-[var(--shadow-2)]"
            } disabled:opacity-50`}
          >
            <Icon size={18} strokeWidth={1.8} />
            {label}
          </button>
        ))}
      </div>

      <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-2)] min-h-[200px]">
        {loading ? (
          <div className="flex items-center gap-3 text-[var(--muted-foreground)]">
            <Loader2 className="animate-spin shrink-0" size={22} aria-hidden />
            <span className="text-sm">Генерируем рецепт…</span>
          </div>
        ) : recipe != null ? (
          <pre className="whitespace-pre-wrap text-sm text-[var(--foreground)] leading-relaxed font-[family-name:var(--font-body)]">
            {recipe}
          </pre>
        ) : (
          <p className="text-sm text-[var(--muted-foreground)]">
            Выберите приём пищи — появится рецепт.
          </p>
        )}
      </div>
    </div>
  );
}
