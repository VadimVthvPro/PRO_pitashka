/* eslint-disable react/no-unescaped-entities */
"use client";

import { useState } from "react";
import { brand } from "@/lib/brand";

type Font = "pobeda" | "arkhip" | "appetite";

const FONT_CLASS: Record<Font, string> = {
  pobeda: "font-[var(--font-pobeda-stack)] tracking-tight",
  arkhip: "font-[var(--font-arkhip-stack)]",
  appetite: "font-[var(--font-appetite-stack)]",
};

const FONT_LABEL: Record<Font, string> = {
  pobeda: "POBEDA BOLD",
  arkhip: "Arkhip",
  appetite: "Appetite",
};

const FONT_NOTES: Record<Font, string> = {
  pobeda: "Широкий, жирный, плакатный. Кричит характером.",
  arkhip: "Геометрический кириллический дисплейный. Сдержанный, с характером.",
  appetite: "Декоративный, «вкусный», food-themed.",
};

function Sample({ font }: { font: Font }) {
  const cls = FONT_CLASS[font];
  return (
    <section className="bg-card border border-card-border rounded-lg p-8 shadow-[var(--shadow-1)]">
      <header className="mb-6 flex items-baseline justify-between">
        <h2 className={`text-5xl ${cls}`}>{FONT_LABEL[font]}</h2>
        <span className="text-sm text-muted">{FONT_NOTES[font]}</span>
      </header>

      {/* Hero-заголовок */}
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-xs uppercase tracking-widest text-muted mb-2">Hero / Brand</div>
        <h1 className={`text-7xl leading-[0.95] ${cls}`}>{brand.displayName}</h1>
        <p className={`text-3xl mt-2 ${cls}`}>Твоя форма — твоя формула</p>
      </div>

      {/* Заголовки секций */}
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-xs uppercase tracking-widest text-muted mb-2">Заголовок секции</div>
        <h3 className={`text-4xl ${cls}`}>Сегодня</h3>
        <h3 className={`text-4xl ${cls} mt-2`}>Прогресс за неделю</h3>
      </div>

      {/* Большие метрики */}
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-xs uppercase tracking-widest text-muted mb-4">Метрики на Dashboard</div>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className={`text-6xl ${cls}`}>1540</div>
            <div className="text-sm text-muted mt-1">ккал / 2100</div>
          </div>
          <div>
            <div className={`text-6xl ${cls}`}>6</div>
            <div className="text-sm text-muted mt-1">стаканов воды</div>
          </div>
          <div>
            <div className={`text-6xl ${cls}`}>72.4</div>
            <div className="text-sm text-muted mt-1">кг • цель 70</div>
          </div>
        </div>
      </div>

      {/* Подзаголовки / навигация */}
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-xs uppercase tracking-widest text-muted mb-2">Навигация / Табы</div>
        <div className={`flex gap-6 text-2xl ${cls}`}>
          <span className="text-accent">Питание</span>
          <span>Тренировки</span>
          <span>Прогресс</span>
          <span>Рецепты</span>
        </div>
      </div>

      {/* Акценты и короткие фразы */}
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-xs uppercase tracking-widest text-muted mb-2">Акценты / фирменные моменты</div>
        <p className={`text-4xl ${cls} text-accent`}>7 дней подряд. Огонь!</p>
        <p className={`text-2xl ${cls} mt-3`}>Норма воды выполнена</p>
        <p className={`text-3xl ${cls} mt-3`}>Завтрак · 420 ккал</p>
      </div>

      {/* Шкала */}
      <div>
        <div className="text-xs uppercase tracking-widest text-muted mb-2">Шкала (0–9 + латиница)</div>
        <div className={`text-3xl ${cls} leading-tight`}>
          АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ
          <br />
          абвгдеёжзийклмнопрстуфхцчшщъыьэюя
          <br />
          ABCDEFGHIJKLMNOPQRSTUVWXYZ
          <br />
          0 1 2 3 4 5 6 7 8 9 · % + − / × = : ( ) « » — ,
        </div>
      </div>
    </section>
  );
}

function CompositeSample({
  display,
  secondary,
  accent,
}: {
  display: Font;
  secondary: Font;
  accent: Font;
}) {
  return (
    <section className="bg-card border-2 border-accent rounded-lg p-8 shadow-[var(--shadow-2)]">
      <div className="text-xs uppercase tracking-widest text-accent mb-4 font-semibold">
        Пример: Dashboard в сборе
      </div>
      <h1
        className={`text-6xl leading-[0.95] ${FONT_CLASS[display]}`}
      >
        Доброе утро, Вадим
      </h1>
      <p className="text-lg text-muted mt-2">Понедельник, 17 апреля</p>

      <div className="grid grid-cols-3 gap-6 mt-10">
        <div className="rounded-lg p-5 bg-[var(--color-cream)] border border-border">
          <div className="text-xs uppercase tracking-widest text-muted">Калории</div>
          <div className={`text-5xl mt-3 ${FONT_CLASS[display]} text-accent`}>1540</div>
          <div className="text-sm text-muted mt-1">из 2100 ккал</div>
        </div>
        <div className="rounded-lg p-5 bg-[var(--color-cream)] border border-border">
          <div className="text-xs uppercase tracking-widest text-muted">Белки</div>
          <div className={`text-5xl mt-3 ${FONT_CLASS[display]} text-[var(--color-sage)]`}>
            98
          </div>
          <div className="text-sm text-muted mt-1">из 140 г</div>
        </div>
        <div className="rounded-lg p-5 bg-[var(--color-cream)] border border-border">
          <div className="text-xs uppercase tracking-widest text-muted">Вода</div>
          <div className={`text-5xl mt-3 ${FONT_CLASS[display]}`}>6</div>
          <div className="text-sm text-muted mt-1">из 8 стаканов</div>
        </div>
      </div>

      <div className="mt-10">
        <h2 className={`text-3xl ${FONT_CLASS[secondary]}`}>Сегодня на сковороде</h2>
        <p className={`text-xl mt-3 ${FONT_CLASS[accent]} text-accent`}>
          7 дней стрика · так держать!
        </p>
      </div>
    </section>
  );
}

export default function FontsPreviewPage() {
  const [display, setDisplay] = useState<Font>("pobeda");
  const [secondary, setSecondary] = useState<Font>("arkhip");
  const [accent, setAccent] = useState<Font>("appetite");

  return (
    <div className="min-h-screen bg-background text-foreground py-10 px-6 lg:px-16">
      <div className="max-w-6xl mx-auto space-y-10">
        <header className="border-b border-border pb-6">
          <h1 className="text-4xl font-display font-bold">Превью шрифтов</h1>
          <p className="text-muted mt-2 max-w-2xl">
            Три ваших кастомных шрифта в реальных контекстах сайта.
            Ниже соберите финальный маппинг и сообщите мне — применю в дизайн-систему.
          </p>
        </header>

        {/* Sample blocks */}
        <Sample font="pobeda" />
        <Sample font="arkhip" />
        <Sample font="appetite" />

        {/* Composite picker */}
        <div className="sticky top-4 z-10 bg-card border border-card-border rounded-lg p-4 shadow-[var(--shadow-2)]">
          <div className="text-xs uppercase tracking-widest text-muted mb-3">
            Соберите свой комбо — превью обновится
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <label className="flex flex-col gap-1">
              <span className="text-muted">Display (hero, числа):</span>
              <select
                value={display}
                onChange={(e) => setDisplay(e.target.value as Font)}
                className="bg-[var(--color-cream)] border border-border rounded px-3 py-2"
              >
                <option value="pobeda">Pobeda Bold</option>
                <option value="arkhip">Arkhip</option>
                <option value="appetite">Appetite</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-muted">Secondary (заголовки секций):</span>
              <select
                value={secondary}
                onChange={(e) => setSecondary(e.target.value as Font)}
                className="bg-[var(--color-cream)] border border-border rounded px-3 py-2"
              >
                <option value="arkhip">Arkhip</option>
                <option value="pobeda">Pobeda Bold</option>
                <option value="appetite">Appetite</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-muted">Accent (стрики, badges):</span>
              <select
                value={accent}
                onChange={(e) => setAccent(e.target.value as Font)}
                className="bg-[var(--color-cream)] border border-border rounded px-3 py-2"
              >
                <option value="appetite">Appetite</option>
                <option value="arkhip">Arkhip</option>
                <option value="pobeda">Pobeda Bold</option>
              </select>
            </label>
          </div>
        </div>

        <CompositeSample display={display} secondary={secondary} accent={accent} />

        <footer className="text-sm text-muted text-center pt-8 pb-4">
          Определились? Скажите: «Display — X, Secondary — Y, Accent — Z» — применяю.
        </footer>
      </div>
    </div>
  );
}
