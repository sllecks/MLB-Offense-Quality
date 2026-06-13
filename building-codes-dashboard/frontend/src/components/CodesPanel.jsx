import {
  Building2,
  Droplets,
  ExternalLink,
  Flame,
  Home,
  Info,
  MapPin,
  Wind,
  Zap,
} from "lucide-react";

const ICON_MAP = {
  Building2,
  Home,
  Zap,
  Wind,
  Droplets,
  Flame,
};

const COLOR_MAP = {
  blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  green: "bg-green-500/10 text-green-400 border-green-500/20",
  yellow: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  cyan: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  red: "bg-red-500/10 text-red-400 border-red-500/20",
};

const BADGE_COLOR_MAP = {
  blue: "bg-blue-900/50 text-blue-300",
  green: "bg-green-900/50 text-green-300",
  yellow: "bg-yellow-900/50 text-yellow-300",
  purple: "bg-purple-900/50 text-purple-300",
  cyan: "bg-cyan-900/50 text-cyan-300",
  red: "bg-red-900/50 text-red-300",
};

export default function CodesPanel({ result }) {
  const { jurisdiction, codes, notes } = result;

  return (
    <div className="p-4 space-y-4">
      {/* Jurisdiction header */}
      <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1">Jurisdiction</p>
            <p className="text-sm text-white font-medium leading-snug">
              {jurisdiction.city ? `${jurisdiction.city}, ` : ""}
              {jurisdiction.state}
            </p>
            {jurisdiction.county && (
              <p className="text-xs text-gray-400 mt-0.5">{jurisdiction.county}</p>
            )}
          </div>
        </div>
      </div>

      {/* Notes */}
      {notes && (
        <div className="bg-amber-950/30 border border-amber-800/40 rounded-lg p-3 flex gap-2">
          <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-200 leading-relaxed">{notes}</p>
        </div>
      )}

      {/* Code count */}
      <div>
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
          Applicable Codes ({codes.length})
        </p>

        <div className="space-y-2">
          {codes.map((code) => {
            const Icon = ICON_MAP[code.icon] || Building2;
            const colorClasses = COLOR_MAP[code.color] || COLOR_MAP.blue;
            const badgeClasses = BADGE_COLOR_MAP[code.color] || BADGE_COLOR_MAP.blue;

            return (
              <a
                key={code.category}
                href={code.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-lg p-3 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-none w-8 h-8 rounded-md border flex items-center justify-center ${colorClasses}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-medium text-gray-300">{code.category}</p>
                      <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0 mt-0.5 transition-colors" />
                    </div>
                    <p className="text-xs text-white font-medium mt-0.5 leading-tight">{code.name}</p>
                    <span className={`inline-block mt-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeClasses}`}>
                      Based on {code.based_on}
                    </span>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      </div>

      <p className="text-[10px] text-gray-600 leading-relaxed pb-2">
        Code adoption data is approximate. Always verify with local authorities having jurisdiction (AHJ).
        Links open the UpCodes viewer for the full code text.
      </p>
    </div>
  );
}
