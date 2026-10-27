import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ReportIssueModal } from "@/components/ReportIssueModal";

export const metadata: Metadata = {
  title: "Nivesh — Indian Equity Research",
  description:
    "Source-linked company research, financial comparisons, transparent backtesting and a personal trade journal for Indian markets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-bg text-neutralText antialiased flex flex-col min-h-screen">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-surface focus:p-3"
        >
          Skip to content
        </a>
        <Header />
        <main
          id="main-content"
          className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6"
        >
          {children}
        </main>
        <Footer />
        <ReportIssueModal />
      </body>
    </html>
  );
}
