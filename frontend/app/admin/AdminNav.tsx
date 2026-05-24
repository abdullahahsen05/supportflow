"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  exactMatch: boolean;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/admin",
    label: "Dashboard",
    exactMatch: true,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: "/admin/knowledge-base",
    label: "Knowledge Base",
    exactMatch: false,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
  },
  {
    href: "/admin",
    label: "Conversations",
    exactMatch: false,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
  },
];

export default function AdminNav() {
  const path = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* Brand */}
      <div className="border-b border-slate-100 px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
            <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">SupportFlow AI</div>
            <div className="text-xs text-slate-400">Admin Console</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-3 py-4">
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Operations
        </p>
        {NAV_ITEMS.map(({ href, label, exactMatch, icon }) => {
          const active = label === "Conversations"
            ? path.startsWith("/admin/conversations")
            : exactMatch
              ? path === href
              : path.startsWith(href);
          return (
            <Link
              key={label}
              href={href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
              }`}
            >
              <span className={active ? "text-indigo-600" : "text-slate-400"}>
                {icon}
              </span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-100 px-5 py-4">
        <Link
          href="/chat"
          className="flex items-center gap-2 text-xs text-slate-400 transition-colors hover:text-indigo-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Customer Chat
        </Link>
      </div>
    </aside>
  );
}
