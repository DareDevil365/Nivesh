"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface StockResult {
  ticker: string;
  name: string;
  sector: string;
  industry?: string;
}

interface SearchAutocompleteProps {
  placeholder?: string;
  className?: string;
  onSelect?: (ticker: string) => void;
}

export const SearchAutocomplete: React.FC<SearchAutocompleteProps> = ({
  placeholder = "Search NSE stocks (e.g., RELIANCE, TCS, INFY)...",
  className = "",
  onSelect,
}) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const router = useRouter();
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await api.get<{ results: StockResult[] }>(
          `/api/companies/search?q=${encodeURIComponent(query.trim())}`
        );
        setResults(data.results || []);
        setIsOpen(true);
      } catch (err) {
        // Fallback ticker creation
        const clean = query.trim().toUpperCase().replace(".NS", "");
        setResults([
          {
            ticker: `${clean}.NS`,
            name: `${clean} (NSE Listed)`,
            sector: "NSE Equity",
          },
        ]);
        setIsOpen(true);
      } finally {
        setIsLoading(false);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (ticker: string) => {
    setIsOpen(false);
    setQuery("");
    if (onSelect) {
      onSelect(ticker);
    } else {
      router.push(`/stock/${ticker}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelect(results[selectedIndex].ticker);
      } else if (results.length > 0) {
        handleSelect(results[0].ticker);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div ref={wrapperRef} className={`relative w-full ${className}`}>
      <div className="relative flex items-center">
        <Search className="absolute left-3 w-4 h-4 text-mutedText" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim() && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Search NSE stocks"
          className="w-full bg-surface border border-border rounded-lg pl-9 pr-8 py-2 text-sm text-neutralText placeholder-mutedText focus:outline-none focus:border-primary transition-colors"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 w-4 h-4 text-primary animate-spin" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-xl max-h-72 overflow-y-auto divide-y divide-border/50">
          {results.map((item, idx) => (
            <button
              key={item.ticker}
              onClick={() => handleSelect(item.ticker)}
              className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${
                idx === selectedIndex
                  ? "bg-primary/20 text-neutralText"
                  : "hover:bg-primary/10 text-neutralText"
              }`}
            >
              <div>
                <span className="font-semibold text-primary">{item.ticker.replace(".NS", "")}</span>
                <span className="text-xs text-mutedText ml-2 truncate max-w-[200px] inline-block align-bottom">
                  {item.name}
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-border text-mutedText">
                {item.sector}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
