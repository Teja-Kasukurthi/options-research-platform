"use client";

import { usePathname } from "next/navigation";
import { Nav } from "./Nav";

const NO_NAV = ["/login"];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (NO_NAV.includes(pathname)) return <>{children}</>;

  return (
    <div className="flex min-h-screen">
      <Nav />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
