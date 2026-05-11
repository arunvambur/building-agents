import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Viz Agent",
  description: "Data visualization assistant powered by LangGraph",
};

// Injected before React hydrates — reads localStorage and applies the
// dark class synchronously to avoid a flash of wrong theme on load.
const themeScript = `
  (function() {
    try {
      var theme = localStorage.getItem('viz-agent-theme');
      if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      }
    } catch(e) {}
  })();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-full">{children}</body>
    </html>
  );
}
