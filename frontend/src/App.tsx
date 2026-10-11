import { useState } from "react";

import ProductChecksPanel from "./components/ProductChecksPanel";
import HomePage from "./pages/HomePage";

type View = "cleaning" | "product-checks";

const views: Array<{ view: View; label: string }> = [
  { view: "cleaning", label: "Data cleaning" },
  { view: "product-checks", label: "CDR product checks" },
];

function initialView(): View {
  return window.location.hash === "#product-checks" ? "product-checks" : "cleaning";
}

export default function App() {
  const [view, setView] = useState<View>(initialView);
  // Mount the checks panel on first visit, then keep its state while hidden.
  const [checksOpened, setChecksOpened] = useState(view === "product-checks");

  function select(next: View) {
    setView(next);
    if (next === "product-checks") setChecksOpened(true);
    const { pathname, search } = window.location;
    const hash = next === "cleaning" ? "" : `#${next}`;
    window.history.replaceState(null, "", `${pathname}${search}${hash}`);
  }

  return (
    <>
      <nav className="app-views" role="tablist" aria-label="Workspaces">
        {views.map((item) => (
          <button
            key={item.view}
            className={item.view === view ? "app-view active" : "app-view"}
            type="button"
            role="tab"
            aria-selected={item.view === view}
            onClick={() => select(item.view)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div hidden={view !== "cleaning"}>
        <HomePage />
      </div>
      {checksOpened && (
        <main className="app-shell" hidden={view !== "product-checks"}>
          <ProductChecksPanel />
        </main>
      )}
    </>
  );
}
