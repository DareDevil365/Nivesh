"use client";
import { useRouter } from "next/navigation";
import StockSearchInput from "./StockSearchInput";
export function SearchAutocomplete({
  placeholder = "Search companies…",
  className = "",
  onSelect,
}: {
  placeholder?: string;
  className?: string;
  onSelect?: (ticker: string) => void;
}) {
  const router = useRouter();
  return (
    <StockSearchInput
      placeholder={placeholder}
      className={className}
      buttonText=""
      onSelectTicker={(ticker) => {
        onSelect?.(ticker);
        router.push(`/stock/${encodeURIComponent(ticker)}`);
      }}
    />
  );
}
