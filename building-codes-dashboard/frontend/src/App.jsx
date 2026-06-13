import { Building2 } from "lucide-react";
import { useState } from "react";
import AddressSearch from "./components/AddressSearch";
import ChatPanel from "./components/ChatPanel";
import CodesPanel from "./components/CodesPanel";

export default function App() {
  const [lookupResult, setLookupResult] = useState(null);
  const [isLooking, setIsLooking] = useState(false);
  const [lookupError, setLookupError] = useState("");

  async function handleSearch(address) {
    setIsLooking(true);
    setLookupError("");
    setLookupResult(null);

    try {
      const res = await fetch("/api/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Lookup failed");
      }

      const data = await res.json();
      setLookupResult(data);
    } catch (e) {
      setLookupError(e.message);
    } finally {
      setIsLooking(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="flex-none border-b border-gray-800 bg-gray-900 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-600">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white leading-none">Building Codes Dashboard</h1>
            <p className="text-xs text-gray-400 mt-0.5">Search any US address to explore applicable building codes</p>
          </div>
        </div>
      </header>

      {/* Search bar */}
      <div className="flex-none border-b border-gray-800 bg-gray-900/50 px-6 py-4">
        <AddressSearch onSearch={handleSearch} isLoading={isLooking} error={lookupError} />
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {lookupResult ? (
          <>
            {/* Left: Codes panel */}
            <div className="w-80 flex-none border-r border-gray-800 overflow-y-auto scrollbar-thin">
              <CodesPanel result={lookupResult} />
            </div>

            {/* Right: Chat panel */}
            <div className="flex-1 overflow-hidden">
              <ChatPanel result={lookupResult} />
            </div>
          </>
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-6 p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center">
        <Building2 className="w-8 h-8 text-gray-500" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-gray-200 mb-2">Enter an Address to Get Started</h2>
        <p className="text-gray-400 max-w-md leading-relaxed">
          Search any US address to see the applicable building codes for that jurisdiction, then use
          the chat interface to ask detailed questions sourced directly from those codes.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-3 mt-4">
        {[
          { label: "Building Codes", desc: "IBC, state & local" },
          { label: "Residential", desc: "IRC & amendments" },
          { label: "Energy Codes", desc: "IECC requirements" },
          { label: "Mechanical", desc: "IMC standards" },
          { label: "Plumbing", desc: "IPC & UPC codes" },
          { label: "Fire Codes", desc: "IFC & NFPA" },
        ].map((item) => (
          <div key={item.label} className="bg-gray-900 rounded-lg p-3 text-left border border-gray-800">
            <div className="text-sm font-medium text-gray-200">{item.label}</div>
            <div className="text-xs text-gray-500 mt-0.5">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
