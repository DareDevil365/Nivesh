"use client";
import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
type Result = { ticker: string; name: string; sector: string };
export default function StockSearchInput({
  placeholder = "Company or exchange symbol",
  className = "",
  onSelectTicker,
  initialValue = "",
  buttonText = "Open research",
}: {
  placeholder?: string;
  className?: string;
  onSelectTicker?: (ticker: string) => void;
  initialValue?: string;
  buttonText?: string;
}) {
  const id = useId();
  const router = useRouter();
  const wrapper = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState(initialValue);
  const [results, setResults] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(-1);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setResults([]);
    setSelected(-1);
    setError("");
    if (!query.trim()) {
      setOpen(false);
      setLoading(false);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.get<{ results: Result[] }>(
          `/api/companies/search?q=${encodeURIComponent(query.trim())}`,
        );
        if (active) {
          setResults(data.results);
          setOpen(true);
        }
      } catch (e) {
        if (active) {
          setError((e as Error).message);
          setOpen(true);
        }
      } finally {
        if (active) setLoading(false);
      }
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);
  useEffect(() => {
    const outside = (event: MouseEvent) => {
      if (wrapper.current && !wrapper.current.contains(event.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, []);
  const choose = (ticker: string) => {
    setOpen(false);
    setQuery("");
    if (onSelectTicker) onSelectTicker(ticker);
    else router.push(`/stock/${encodeURIComponent(ticker)}`);
  };
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    if (results.length) {
      choose(results[selected >= 0 ? selected : 0].ticker);
      return;
    }
    const symbol = query.trim().toUpperCase();
    if (!/^[A-Z0-9&][A-Z0-9&.\-]{0,29}$/.test(symbol)) {
      setError("Choose a matching company or enter a valid exchange symbol.");
      setOpen(true);
      return;
    }
    choose(
      symbol.endsWith(".NS") || symbol.endsWith(".BO")
        ? symbol
        : `${symbol}.NS`,
    );
  };
  return (
    <div ref={wrapper} className={`relative ${className}`}>
      <form onSubmit={submit} className="flex gap-2">
        <input
          role="combobox"
          aria-label="Search company or symbol"
          aria-expanded={open}
          aria-controls={`${id}-results`}
          aria-autocomplete="list"
          aria-activedescendant={
            selected >= 0 ? `${id}-option-${selected}` : undefined
          }
          maxLength={60}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim() && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              return;
            }
            if (!results.length) return;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSelected((i) => (i + 1) % results.length);
              setOpen(true);
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setSelected((i) => (i <= 0 ? results.length - 1 : i - 1));
              setOpen(true);
            }
          }}
          placeholder={placeholder}
          className="w-full min-w-0 bg-bg border border-border rounded-lg px-3 py-2.5 text-xs sm:text-sm"
        />
        {buttonText && (
          <button
            type="submit"
            disabled={!query.trim()}
            className="bg-primary text-white rounded-lg px-4 py-2 text-xs font-semibold shrink-0 disabled:opacity-40"
          >
            {buttonText}
          </button>
        )}
      </form>
      {open && (
        <div className="absolute z-50 top-full mt-2 left-0 right-0 bg-surface border border-border rounded-lg shadow-xl max-h-72 overflow-y-auto">
          <ul
            id={`${id}-results`}
            role="listbox"
            aria-label="Matching companies"
          >
            {results.map((r, i) => (
              <li
                key={r.ticker}
                id={`${id}-option-${i}`}
                role="option"
                aria-selected={selected === i}
              >
                <button
                  type="button"
                  onClick={() => choose(r.ticker)}
                  onMouseEnter={() => setSelected(i)}
                  className={`w-full text-left p-3 border-b border-border text-xs ${selected === i ? "bg-primary/15" : "hover:bg-bg"}`}
                >
                  <strong className="text-positive">{r.ticker}</strong>
                  <p className="text-neutralText mt-1">{r.name}</p>
                  <span className="text-mutedText text-[10px]">{r.sector}</span>
                </button>
              </li>
            ))}
          </ul>
          {loading && (
            <p className="p-3 text-xs text-mutedText" role="status">
              Searching…
            </p>
          )}
          {error && (
            <p className="p-3 text-xs text-amber-300" role="status">
              {error}
            </p>
          )}
          {!loading && !error && !results.length && (
            <p className="p-3 text-xs text-mutedText">
              No verified matches. You can enter an exchange symbol to try it
              directly.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
