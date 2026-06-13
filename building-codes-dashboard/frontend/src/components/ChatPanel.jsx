import { ArrowUp, BookOpen, Loader2, MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

function SourceCard({ source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 rounded-lg p-3 transition-colors group"
    >
      <div className="flex items-start gap-2.5">
        <BookOpen className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="text-xs font-semibold text-blue-300">{source.code}</span>
            <span className="text-xs text-gray-400">{source.section}</span>
          </div>
          {source.title && (
            <p className="text-xs font-medium text-gray-200 mt-0.5">{source.title}</p>
          )}
          {source.excerpt && (
            <p className="text-xs text-gray-400 mt-1 leading-relaxed line-clamp-2">{source.excerpt}</p>
          )}
        </div>
      </div>
    </a>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`flex-none w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-200"
        }`}
      >
        {isUser ? "U" : "AI"}
      </div>

      <div className={`flex-1 min-w-0 ${isUser ? "flex flex-col items-end" : ""}`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 max-w-[85%] ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : "bg-gray-800 text-gray-100 rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed">{msg.content}</p>
          ) : (
            <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="mt-3 w-full max-w-[85%]">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Sources ({msg.sources.length})
            </p>
            <div className="space-y-1.5">
              {msg.sources.map((src, i) => (
                <SourceCard key={i} source={src} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({ result }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Reset chat when jurisdiction changes
  useEffect(() => {
    setMessages([]);
    setInput("");
    setError("");
  }, [result?.jurisdiction?.display]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSend(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    const userMsg = { role: "user", content: question };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);
    setError("");

    const historyForApi = newMessages.slice(0, -1).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          jurisdiction: result.jurisdiction,
          codes: result,
          history: historyForApi,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Chat request failed");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sources: data.sources || [] },
      ]);
    } catch (e) {
      setError(e.message);
      setMessages((prev) => prev.slice(0, -1));
      setInput(question);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  const jurisdiction = result?.jurisdiction;

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div className="flex-none border-b border-gray-800 px-5 py-3 bg-gray-900/30">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">
            Ask about building codes for{" "}
            <span className="text-white">
              {jurisdiction?.city ? `${jurisdiction.city}, ` : ""}
              {jurisdiction?.state}
            </span>
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-gray-500" />
            </div>
            <div>
              <p className="text-gray-300 font-medium">Ask a building code question</p>
              <p className="text-sm text-gray-500 mt-1">
                All answers are sourced from the applicable codes for this jurisdiction.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
              {[
                "What is the minimum ceiling height for habitable rooms?",
                "What are the egress window requirements for bedrooms?",
                "What insulation R-values are required for this climate zone?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="text-left text-xs text-gray-400 hover:text-gray-200 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-3 py-2 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-none w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-200">
              AI
            </div>
            <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              <span className="text-sm text-gray-400">Analyzing building codes…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="flex-none px-5 py-2 bg-red-950/40 border-t border-red-900/50">
          <p className="text-xs text-red-400">
            <span className="font-medium">Error:</span> {error}
          </p>
        </div>
      )}

      {/* Input */}
      <div className="flex-none border-t border-gray-800 bg-gray-900/30 p-4">
        <form onSubmit={handleSend} className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            placeholder="Ask a question about building codes… (Enter to send)"
            rows={2}
            className="flex-1 resize-none bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors scrollbar-thin"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex-none w-10 h-10 flex items-center justify-center rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowUp className="w-4 h-4" />
            )}
          </button>
        </form>
        <p className="text-[10px] text-gray-600 mt-2 text-center">
          AI answers are for informational purposes only. Always verify with a licensed professional and local AHJ.
        </p>
      </div>
    </div>
  );
}
