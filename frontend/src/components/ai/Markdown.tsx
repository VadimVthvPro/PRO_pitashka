"use client";

/**
 * Safe Markdown renderer used everywhere we display AI text:
 *  - chat assistant replies
 *  - meal / workout plans
 *  - recipes
 *  - weekly digest summary blocks
 *
 * We restrict the input to the small subset our prompts ask the model to
 * produce (see `backend/app/services/prompts.py::SAFE_MARKDOWN_RULES`):
 * paragraphs, bold/italic, inline code, ordered/unordered lists, headings
 * up to h3, horizontal rules, and `> blockquotes`. Everything else (raw
 * HTML, images, scripts) is sanitised away by `rehype-sanitize`. This keeps
 * the surface area small and the output strictly aligned with the system's
 * visual language defined in DESIGN_GUIDE.md.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

const schema = {
  ...defaultSchema,
  tagNames: [
    "p",
    "br",
    "strong",
    "em",
    "code",
    "pre",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "hr",
    "del",
  ],
  attributes: {
    ...defaultSchema.attributes,
    code: [["className", /^language-/]],
  },
};

interface MarkdownProps {
  children: string;
  /** Tweak font-size etc. for compact contexts (chat bubbles vs full pages). */
  variant?: "compact" | "comfortable";
  className?: string;
}

export function Markdown({ children, variant = "comfortable", className = "" }: MarkdownProps) {
  const proseSize = variant === "compact" ? "prose-sm" : "prose-base";
  return (
    <div
      className={[
        "prose max-w-none break-words",
        proseSize,
        // Force the design-system tokens. Tailwind Typography would also
        // work, but we don't want to depend on it just for this — the
        // ruleset below is intentionally tiny.
        "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        "[&_p]:my-2 [&_p]:leading-relaxed",
        "[&_h1]:text-xl [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2",
        "[&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-4 [&_h2]:mb-2",
        "[&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1.5",
        "[&_h4]:text-sm [&_h4]:font-semibold [&_h4]:mt-2 [&_h4]:mb-1 [&_h4]:uppercase [&_h4]:tracking-wide [&_h4]:text-[var(--muted-foreground)]",
        "[&_strong]:font-semibold [&_strong]:text-[var(--foreground)]",
        "[&_em]:italic [&_em]:text-[var(--muted-foreground)]",
        "[&_ul]:my-2 [&_ul]:pl-5 [&_ul]:list-disc",
        "[&_ol]:my-2 [&_ol]:pl-5 [&_ol]:list-decimal",
        "[&_li]:my-1 [&_li]:leading-relaxed [&_li]:marker:text-[var(--accent)]",
        "[&_li>p]:my-0",
        "[&_hr]:my-4 [&_hr]:border-0 [&_hr]:h-px [&_hr]:bg-[var(--border)]",
        "[&_blockquote]:my-3 [&_blockquote]:pl-4 [&_blockquote]:border-l-2 [&_blockquote]:border-[var(--accent)] [&_blockquote]:italic [&_blockquote]:text-[var(--muted-foreground)]",
        "[&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-[var(--card)] [&_code]:text-[var(--foreground)] [&_code]:text-[0.92em] [&_code]:border [&_code]:border-[var(--border)]",
        "[&_pre]:my-3 [&_pre]:p-3 [&_pre]:rounded-[var(--radius)] [&_pre]:bg-[var(--card)] [&_pre]:border [&_pre]:border-[var(--border)] [&_pre]:overflow-x-auto",
        className,
      ].join(" ")}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, schema]]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
