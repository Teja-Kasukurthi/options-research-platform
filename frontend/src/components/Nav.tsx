"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Layers, BookOpen, FlaskConical, Settings, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMarketStore } from "@/stores/marketStore";

const NAV = [
  { href: "/", label: "Overview", icon: BarChart2 },
  { href: "/signals", label: "Signals", icon: TrendingUp },
  { href: "/positions", label: "Positions", icon: Layers },
  { href: "/research", label: "Research", icon: BookOpen },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Nav() {
  const pathname = usePathname();
  const newSignalCount = useMarketStore((s) => s.newSignalCount);

  return (
    <nav className="flex flex-col gap-1 p-3 w-56 border-r border-border min-h-screen bg-card">
      <div className="px-2 py-3 mb-2">
        <span className="text-sm font-bold tracking-tight text-foreground">Options Research</span>
        <span className="block text-xs text-muted-foreground mt-0.5">Personal · Paper Only</span>
      </div>

      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== "/" && pathname.startsWith(href));
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors relative",
              active
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            <Icon size={16} />
            {label}
            {label === "Signals" && newSignalCount > 0 && (
              <span className="ml-auto text-xs bg-yellow-400 text-black rounded-full px-1.5 py-0.5 font-bold">
                {newSignalCount}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
