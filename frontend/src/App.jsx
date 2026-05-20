import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/examples`)
      .then((res) => res.json())
      .then((data) => setExamples(data.examples || []))
      .catch(() => setExamples([]));
  }, []);

  const stats = useMemo(() => {
    const errors = history.filter((h) => h.error).length;
    return { total: history.length, errors };
  }, [history]);

  const runQuery = async (value) => {
    const text = (value || question).trim();
    if (!text || loading) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: text }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Request failed");
      }

      const result = await response.json();
      setHistory((prev) => [...prev, result]);
      setQuestion("");
    } catch (err) {
      setError(err.message || "Unable to reach backend API.");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (event) => {
    event.preventDefault();
    runQuery();
  };

  const clear = () => {
    setHistory([]);
    setError("");
  };

  return (
    <div className="min-h-screen text-ink font-display">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 md:grid-cols-[280px_minmax(0,1fr)] md:px-6">
        <aside className="h-fit rounded-2xl border border-black/10 bg-white/80 p-5 shadow-card backdrop-blur">
          <h1 className="font-mono text-xs uppercase tracking-[0.2em] text-forest">SQL Agent</h1>
          <p className="mt-2 text-sm leading-relaxed text-black/70">
            Ask plain English questions. Get SQL, tool reasoning, and business answers.
          </p>

          <div className="mt-6 space-y-3">
            <div className="rounded-xl border border-clay/30 bg-clay/10 p-3">
              <p className="font-mono text-[11px] uppercase tracking-widest text-black/60">Queries</p>
              <p className="text-2xl font-bold">{stats.total}</p>
            </div>
            <div className="rounded-xl border border-amber/40 bg-amber/20 p-3">
              <p className="font-mono text-[11px] uppercase tracking-widest text-black/60">Errors</p>
              <p className="text-2xl font-bold">{stats.errors}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={clear}
            className="mt-6 w-full rounded-xl border border-black/20 bg-white px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:bg-black hover:text-white"
          >
            Clear History
          </button>

          <div className="mt-6 rounded-xl bg-forest px-4 py-3 text-paper">
            <p className="font-mono text-[11px] uppercase tracking-widest">Stack</p>
            <p className="mt-2 text-sm">LangChain · Mistral · FastAPI · React · Tailwind</p>
          </div>
        </aside>

        <main className="rounded-3xl border border-black/10 bg-paper/80 p-4 shadow-card backdrop-blur md:p-6">
          <header className="animate-rise">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-forest">AI SQL Agent</p>
            <h2 className="mt-2 text-3xl font-extrabold leading-tight md:text-4xl">
              Ask your Uber Eats data anything
            </h2>
          </header>

          <div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {examples.map((example, index) => (
              <button
                key={example}
                type="button"
                onClick={() => runQuery(example)}
                className="animate-rise rounded-xl border border-forest/20 bg-white px-4 py-3 text-left text-sm transition hover:-translate-y-1 hover:border-forest hover:bg-forest hover:text-white"
                style={{ animationDelay: `${index * 70}ms` }}
              >
                {example}
              </button>
            ))}
          </div>

          <form onSubmit={onSubmit} className="mt-5 flex flex-col gap-3 md:flex-row">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your orders data..."
              className="w-full rounded-xl border border-black/15 bg-white px-4 py-3 text-base outline-none ring-clay/50 transition focus:ring-2"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-ink px-6 py-3 font-semibold text-paper transition hover:-translate-y-0.5 hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Running..." : "Run Query"}
            </button>
          </form>

          {error && (
            <div className="mt-4 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <section className="mt-6 space-y-4">
            {history.length === 0 && (
              <div className="rounded-2xl border border-dashed border-black/20 bg-white/50 px-5 py-8 text-center text-black/60">
                Start with an example or type your own question.
              </div>
            )}

            {history.map((entry, index) => (
              <article
                key={`${entry.question}-${index}`}
                className="animate-rise rounded-2xl border border-black/10 bg-white p-5"
              >
                <div className="rounded-xl border border-clay/30 bg-clay/10 p-3">
                  <p className="font-mono text-[11px] uppercase tracking-widest text-black/60">You</p>
                  <p className="mt-1 text-sm md:text-base">{entry.question}</p>
                </div>

                <div className="mt-3 rounded-xl border border-forest/30 bg-forest/10 p-3">
                  <p className="font-mono text-[11px] uppercase tracking-widest text-black/60">Agent</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm md:text-base">{entry.answer}</p>
                </div>

                {entry.sql && (
                  <div className="mt-3 overflow-hidden rounded-xl border border-black/15">
                    <p className="bg-ink px-3 py-2 font-mono text-xs uppercase tracking-widest text-paper">SQL</p>
                    <pre className="overflow-x-auto bg-black p-3 font-mono text-xs text-green-300">
                      {entry.sql}
                    </pre>
                  </div>
                )}

                {entry.steps?.length > 0 && (
                  <details className="mt-3 rounded-xl border border-black/10 bg-paper px-3 py-2">
                    <summary className="cursor-pointer font-mono text-xs uppercase tracking-widest text-black/70">
                      Reasoning Steps ({entry.steps.length})
                    </summary>
                    <div className="mt-3 space-y-2">
                      {entry.steps.map((step, stepIndex) => (
                        <div
                          key={`${index}-step-${stepIndex}`}
                          className="rounded-lg border border-black/10 bg-white px-3 py-2"
                        >
                          <p className="font-mono text-xs text-black/70">Tool: {String(step[0])}</p>
                          <p className="mt-1 text-xs text-black/60">Input: {String(step[1]).slice(0, 220)}</p>
                          <p className="mt-1 text-xs text-black/60">Obs: {String(step[2]).slice(0, 320)}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </article>
            ))}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
