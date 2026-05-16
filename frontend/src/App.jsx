import { useEffect, useState } from "react";

const serviceUrls = {
  greeter: import.meta.env.VITE_GREETER_URL || "http://localhost:8001",
  math: import.meta.env.VITE_MATH_URL || "http://localhost:8002",
  notes: import.meta.env.VITE_NOTES_URL || "http://localhost:8003",
  inventory: import.meta.env.VITE_INVENTORY_URL || "http://localhost:8004",
  shipping: import.meta.env.VITE_SHIPPING_URL || "http://localhost:8005",
  checkout: import.meta.env.VITE_CHECKOUT_URL || "http://localhost:8006",
};

const defaultHealth = {
  greeter: "unknown",
  math: "unknown",
  notes: "unknown",
  inventory: "unknown",
  shipping: "unknown",
  checkout: "unknown",
};

const checkoutCatalog = [
  { sku: "keyboard", label: "Keyboard", price: 129 },
  { sku: "mouse", label: "Mouse", price: 59 },
  { sku: "monitor", label: "Monitor", price: 349 },
  { sku: "dock", label: "Dock", price: 149 },
];

function createTraceId() {
  return `checkout-demo-${Date.now()}`;
}

function buildCheckoutItems(quantities) {
  return Object.entries(quantities).flatMap(([sku, quantity]) => {
    const normalizedQuantity = Number(quantity);

    if (!Number.isFinite(normalizedQuantity) || normalizedQuantity <= 0) {
      return [];
    }

    return [{ sku, quantity: normalizedQuantity }];
  });
}

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

export default function App() {
  const [health, setHealth] = useState(defaultHealth);
  const [greetingResult, setGreetingResult] = useState(null);
  const [mathResult, setMathResult] = useState(null);
  const [notesResult, setNotesResult] = useState(null);
  const [checkoutResult, setCheckoutResult] = useState(null);
  const [notes, setNotes] = useState([]);

  const [name, setName] = useState("Ada");
  const [style, setStyle] = useState("friendly");
  const [left, setLeft] = useState("8");
  const [right, setRight] = useState("2");
  const [operation, setOperation] = useState("divide");
  const [noteTitle, setNoteTitle] = useState("Run one end-to-end test");
  const [customerId, setCustomerId] = useState("student-42");
  const [postalCode, setPostalCode] = useState("10115");
  const [requestId, setRequestId] = useState(() => createTraceId());
  const [cartQuantities, setCartQuantities] = useState({
    keyboard: "1",
    mouse: "0",
    monitor: "0",
    dock: "1",
  });

  useEffect(() => {
    refreshHealth();
    loadNotes();
  }, []);

  async function refreshHealth() {
    const entries = await Promise.all(
      Object.entries(serviceUrls).map(async ([key, baseUrl]) => {
        try {
          const response = await fetch(`${baseUrl}/health`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return [key, "online"];
        } catch {
          return [key, "offline"];
        }
      }),
    );

    setHealth(Object.fromEntries(entries));
  }

  async function loadNotes() {
    try {
      const response = await fetch(`${serviceUrls.notes}/notes`);
      const data = await response.json();
      setNotes(data.items || []);
      setNotesResult(data);
    } catch (error) {
      setNotesResult({ error: error.message });
    }
  }

  async function handleGreetingSubmit(event) {
    event.preventDefault();

    try {
      const response = await fetch(`${serviceUrls.greeter}/greet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, style }),
      });
      const data = await response.json();
      setGreetingResult(data);
    } catch (error) {
      setGreetingResult({ error: error.message });
    }
  }

  async function handleMathSubmit(event) {
    event.preventDefault();

    try {
      const response = await fetch(`${serviceUrls.math}/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          left: Number(left),
          right: Number(right),
          operation,
        }),
      });
      const data = await response.json();
      setMathResult(data);
    } catch (error) {
      setMathResult({ error: error.message });
    }
  }

  async function handleCreateNote(event) {
    event.preventDefault();

    try {
      const response = await fetch(`${serviceUrls.notes}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: noteTitle }),
      });
      const data = await response.json();
      setNotesResult(data);
      setNoteTitle("");
      await loadNotes();
    } catch (error) {
      setNotesResult({ error: error.message });
    }
  }

  async function handleToggleNote(noteId) {
    try {
      const response = await fetch(`${serviceUrls.notes}/notes/${noteId}/toggle`, {
        method: "POST",
      });
      const data = await response.json();
      setNotesResult(data);
      await loadNotes();
    } catch (error) {
      setNotesResult({ error: error.message });
    }
  }

  function handleCartQuantityChange(sku, value) {
    setCartQuantities((current) => ({
      ...current,
      [sku]: value,
    }));
  }

  async function handleCheckoutSubmit(event) {
    event.preventDefault();

    const items = buildCheckoutItems(cartQuantities);

    if (items.length === 0) {
      setCheckoutResult({ error: "Mindestens ein Artikel mit Menge groesser als 0 ist erforderlich." });
      return;
    }

    const traceId = requestId.trim() || createTraceId();

    if (traceId !== requestId) {
      setRequestId(traceId);
    }

    try {
      const response = await fetch(`${serviceUrls.checkout}/checkout/quote`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": traceId,
        },
        body: JSON.stringify({
          customer_id: customerId,
          postal_code: postalCode,
          items,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      setCheckoutResult(data);
    } catch (error) {
      setCheckoutResult({ error: error.message, request_id: traceId });
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">React + FastAPI + Docker</p>
          <h1>Microservice Test Bench</h1>
          <p className="intro">
            Sechs kleine Demo-Services, ein Frontend und alles in Containern. Der neue
            Checkout-Block startet eine echte Request-Kette ueber mehrere Services hinweg.
          </p>
        </div>
        <button className="secondary-button" onClick={refreshHealth} type="button">
          Status neu laden
        </button>
      </header>

      <section className="status-grid">
        {Object.entries(health).map(([serviceName, state]) => (
          <article className="status-card" key={serviceName}>
            <span className={`status-dot ${state}`} />
            <div>
              <p className="status-label">{serviceName}</p>
              <strong>{state}</strong>
            </div>
          </article>
        ))}
      </section>

      <main className="panel-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Greeter Service</h2>
            <span>{serviceUrls.greeter}</span>
          </div>
          <form onSubmit={handleGreetingSubmit}>
            <label>
              Name
              <input value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label>
              Stil
              <select value={style} onChange={(event) => setStyle(event.target.value)}>
                <option value="friendly">friendly</option>
                <option value="formal">formal</option>
                <option value="casual">casual</option>
              </select>
            </label>
            <button type="submit">POST /greet</button>
          </form>
          <pre>{greetingResult ? prettyJson(greetingResult) : "Noch kein Request."}</pre>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Math Service</h2>
            <span>{serviceUrls.math}</span>
          </div>
          <form onSubmit={handleMathSubmit}>
            <div className="input-row">
              <label>
                Left
                <input value={left} onChange={(event) => setLeft(event.target.value)} />
              </label>
              <label>
                Right
                <input value={right} onChange={(event) => setRight(event.target.value)} />
              </label>
            </div>
            <label>
              Operation
              <select
                value={operation}
                onChange={(event) => setOperation(event.target.value)}
              >
                <option value="add">add</option>
                <option value="subtract">subtract</option>
                <option value="multiply">multiply</option>
                <option value="divide">divide</option>
              </select>
            </label>
            <button type="submit">POST /calculate</button>
          </form>
          <pre>{mathResult ? prettyJson(mathResult) : "Noch kein Request."}</pre>
        </section>

        <section className="panel panel-wide">
          <div className="panel-heading">
            <h2>Checkout Flow</h2>
            <span>{serviceUrls.checkout}</span>
          </div>
          <p className="panel-copy">
            Schickt einen Request an <strong>checkout</strong>, der intern <strong>inventory</strong>
            {" "}und <strong>shipping</strong> aufruft. Die Request-ID kannst du spaeter direkt in
            den Logs suchen.
          </p>
          <form onSubmit={handleCheckoutSubmit}>
            <div className="checkout-grid">
              <label>
                Customer ID
                <input
                  value={customerId}
                  onChange={(event) => setCustomerId(event.target.value)}
                />
              </label>
              <label>
                Postal Code
                <input
                  value={postalCode}
                  onChange={(event) => setPostalCode(event.target.value)}
                />
              </label>
            </div>

            <label>
              Request-ID fuer spaetere Logsuche
              <div className="request-id-row">
                <input
                  value={requestId}
                  onChange={(event) => setRequestId(event.target.value)}
                />
                <button
                  className="ghost-button"
                  onClick={() => setRequestId(createTraceId())}
                  type="button"
                >
                  Neue ID
                </button>
              </div>
            </label>

            <div>
              <p className="field-hint">Warenkorb fuer den Kettenaufruf</p>
              <div className="cart-grid">
                {checkoutCatalog.map((item) => (
                  <label className="cart-item" key={item.sku}>
                    <span>
                      {item.label}
                      <small>{item.sku}</small>
                    </span>
                    <div className="cart-controls">
                      <input
                        min="0"
                        type="number"
                        value={cartQuantities[item.sku]}
                        onChange={(event) => handleCartQuantityChange(item.sku, event.target.value)}
                      />
                      <strong>{item.price} EUR</strong>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <button type="submit">POST /checkout/quote</button>
          </form>

          {checkoutResult && !checkoutResult.error ? (
            <div className="summary-strip">
              <article>
                <span>Trace</span>
                <strong>{checkoutResult.request_id}</strong>
              </article>
              <article>
                <span>Total</span>
                <strong>{checkoutResult.total} EUR</strong>
              </article>
              <article>
                <span>Bereit</span>
                <strong>{checkoutResult.ready_to_checkout ? "ja" : "nein"}</strong>
              </article>
            </div>
          ) : null}

          <pre>{checkoutResult ? prettyJson(checkoutResult) : "Noch kein Request."}</pre>
        </section>

        <section className="panel panel-wide">
          <div className="panel-heading">
            <h2>Notes Service</h2>
            <span>{serviceUrls.notes}</span>
          </div>
          <form onSubmit={handleCreateNote}>
            <label>
              Neue Test-Notiz
              <input
                value={noteTitle}
                onChange={(event) => setNoteTitle(event.target.value)}
                placeholder="Beschreibe einen Testfall"
              />
            </label>
            <button type="submit">POST /notes</button>
          </form>

          <div className="notes-list">
            {notes.map((note) => (
              <button
                className={`note-chip ${note.done ? "done" : ""}`}
                key={note.id}
                onClick={() => handleToggleNote(note.id)}
                type="button"
              >
                <span>#{note.id}</span>
                <strong>{note.title}</strong>
              </button>
            ))}
          </div>

          <pre>{notesResult ? prettyJson(notesResult) : "Noch kein Request."}</pre>
        </section>
      </main>
    </div>
  );
}
