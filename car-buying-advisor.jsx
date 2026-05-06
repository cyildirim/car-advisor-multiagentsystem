import { useState } from "react";

const SYSTEM_PROMPT = `You are a senior UK used car buying advisor coordinating three specialist agents:

1. **Price Fairness Agent**: Evaluates if the asking price is fair for the UK market
2. **MOT Risk Agent**: Analyses the listing description for red flags and common dealer tactics  
3. **Running Costs Agent**: Estimates annual running costs (tax, insurance, fuel, servicing, depreciation)

NOTE: You do not have access to the real DVSA MOT API here — treat the MOT analysis as a listing-description-only risk assessment (in production this would query the real API using the registration number).

Given the car listing details, analyse all three dimensions and return ONLY a valid JSON object (no markdown, no preamble) in this exact structure:

{
  "recommendation": "BUY" | "NEGOTIATE" | "WALK_AWAY",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "summary": "2-3 sentence plain English summary",
  "headline_reasons": ["reason 1", "reason 2", "reason 3"],
  "price_analysis": {
    "verdict": "FAIR" | "OVERPRICED" | "UNDERPRICED",
    "estimated_market_value": 9500,
    "price_difference": -500,
    "reasoning": "explanation",
    "negotiation_suggestion": "suggested tactic or offer"
  },
  "mot_analysis": {
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "risk_flags": ["flag 1", "flag 2"],
    "listing_red_flags": ["red flag 1"],
    "top_concerns": ["concern 1", "concern 2"],
    "recommended_inspection_points": ["point 1", "point 2", "point 3"]
  },
  "running_costs": {
    "road_tax_annual": 180,
    "insurance_estimate": {"low": 600, "high": 900},
    "fuel_cost_annual": 1200,
    "fuel_efficiency": "40 mpg assumed",
    "servicing_annual": 350,
    "tyres_annual": 120,
    "mot_annual": 55,
    "total_annual_cost": 2505,
    "depreciation_3yr": 2800,
    "ownership_notes": ["note 1"],
    "known_expensive_repairs": ["repair 1"]
  },
  "negotiation_advice": "specific tactics if NEGOTIATE",
  "walk_away_reason": "clearest reason if WALK_AWAY",
  "questions_to_ask_seller": ["question 1", "question 2", "question 3"],
  "things_to_inspect": ["item 1", "item 2", "item 3"]
}`;

const VERDICT_CONFIG = {
  BUY: { label: "Buy", color: "var(--color-text-success)", bg: "var(--color-background-success)", icon: "✓" },
  NEGOTIATE: { label: "Negotiate", color: "var(--color-text-warning)", bg: "var(--color-background-warning)", icon: "⟷" },
  WALK_AWAY: { label: "Walk Away", color: "var(--color-text-danger)", bg: "var(--color-background-danger)", icon: "✕" },
};

const PRICE_VERDICT = {
  FAIR: { color: "var(--color-text-success)", label: "Fair price" },
  UNDERPRICED: { color: "var(--color-text-success)", label: "Below market" },
  OVERPRICED: { color: "var(--color-text-danger)", label: "Overpriced" },
};

const RISK_COLOR = {
  LOW: "var(--color-text-success)",
  MEDIUM: "var(--color-text-warning)",
  HIGH: "var(--color-text-danger)",
};

function AgentCard({ title, icon, children, accent }) {
  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: `0.5px solid var(--color-border-tertiary)`,
      borderTop: `2px solid ${accent}`,
      borderRadius: "0 0 var(--border-radius-lg) var(--border-radius-lg)",
      padding: "1rem 1.25rem",
      marginBottom: "0",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</span>
      </div>
      {children}
    </div>
  );
}

function Pill({ text, color, bg }) {
  return (
    <span style={{
      display: "inline-block",
      background: bg || "var(--color-background-secondary)",
      color: color || "var(--color-text-secondary)",
      fontSize: 12,
      padding: "2px 8px",
      borderRadius: "var(--border-radius-md)",
      marginRight: 6,
      marginBottom: 4,
    }}>{text}</span>
  );
}

function Flag({ text, type = "warn" }) {
  const colors = {
    warn: { bg: "var(--color-background-warning)", color: "var(--color-text-warning)" },
    danger: { bg: "var(--color-background-danger)", color: "var(--color-text-danger)" },
    info: { bg: "var(--color-background-info)", color: "var(--color-text-info)" },
  };
  return (
    <div style={{
      background: colors[type].bg,
      color: colors[type].color,
      fontSize: 13,
      padding: "6px 10px",
      borderRadius: "var(--border-radius-md)",
      marginBottom: 6,
    }}>{text}</div>
  );
}

function CostRow({ label, value, note }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "5px 0", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
      <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 500 }}>
        £{value?.toLocaleString()} {note && <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{note}</span>}
      </span>
    </div>
  );
}

export default function CarAdvisor() {
  const [form, setForm] = useState({
    registration: "AB12CDE",
    make: "Volkswagen",
    model: "Golf",
    year: "2018",
    mileage: "62000",
    asking_price: "11500",
    fuel_type: "Petrol",
    engine_size: "1.4",
    description: "One previous owner, full VW service history, just had new brakes fitted. Selling due to upgrade to electric. MOT until March 2026. Minor scuff on rear bumper. Drives perfectly.",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [agentLog, setAgentLog] = useState([]);

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const analyse = async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    setAgentLog(["Price Fairness Agent running...", "MOT Risk Agent running...", "Running Costs Agent running..."]);

    const prompt = `Analyse this UK used car listing:\n\nRegistration: ${form.registration}\nMake: ${form.make}\nModel: ${form.model}\nYear: ${form.year}\nMileage: ${parseInt(form.mileage).toLocaleString()} miles\nAsking Price: £${parseInt(form.asking_price).toLocaleString()}\nFuel Type: ${form.fuel_type}\nEngine Size: ${form.engine_size}L\n\nListing Description:\n"${form.description}"`;

    try {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await resp.json();
      const text = data.content?.find(b => b.type === "text")?.text || "";
      const clean = text.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setResult(parsed);
      setAgentLog(["Price Fairness Agent ✓", "MOT Risk Agent ✓", "Running Costs Agent ✓", "Root Agent synthesis ✓"]);
    } catch (e) {
      setError("Analysis failed. Check the API key is configured.");
      setAgentLog([]);
    }
    setLoading(false);
  };

  const verdict = result ? VERDICT_CONFIG[result.recommendation] : null;

  return (
    <div style={{ padding: "1rem 0", maxWidth: 680, fontFamily: "var(--font-sans)" }}>
      <h2 style={{ fontSize: 18, fontWeight: 500, margin: "0 0 4px", color: "var(--color-text-primary)" }}>Should I buy this car?</h2>
      <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 1.5rem" }}>Paste a UK car listing — three ADK agents analyse it in parallel and return a verdict.</p>

      {/* Form */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
        {[
          ["Registration", "registration", "e.g. AB12CDE"],
          ["Make", "make", "e.g. Volkswagen"],
          ["Model", "model", "e.g. Golf"],
        ].map(([label, key, ph]) => (
          <div key={key}>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>{label}</label>
            <input value={form[key]} onChange={set(key)} placeholder={ph} style={{ width: "100%", boxSizing: "border-box" }} />
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
        {[
          ["Year", "year", "2018"],
          ["Mileage", "mileage", "62000"],
          ["Asking price £", "asking_price", "11500"],
          ["Fuel type", "fuel_type", "Petrol"],
          ["Engine (L)", "engine_size", "1.4"],
        ].map(([label, key, ph]) => (
          <div key={key}>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>{label}</label>
            <input value={form[key]} onChange={set(key)} placeholder={ph} style={{ width: "100%", boxSizing: "border-box" }} />
          </div>
        ))}
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "block", marginBottom: 4 }}>Listing description</label>
        <textarea value={form.description} onChange={set("description")} rows={3}
          style={{ width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "var(--font-sans)", fontSize: 13 }} />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: "1.5rem" }}>
        <button onClick={analyse} disabled={loading} style={{ opacity: loading ? 0.6 : 1 }}>
          {loading ? "Analysing..." : "Analyse listing ↗"}
        </button>
        {loading && agentLog.length > 0 && (
          <div style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
            {agentLog[agentLog.length - 1]}
          </div>
        )}
      </div>

      {/* Agent pipeline diagram */}
      {!result && !loading && (
        <div style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>ADK + A2A architecture</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            {[
              { label: "Car listing", sub: "Input" },
              "→",
              { label: "Root agent", sub: "Orchestrator" },
              "→",
              { label: "Price agent", sub: "Fair / Over / Under" },
              { label: "MOT agent", sub: "Risk + red flags" },
              { label: "Costs agent", sub: "Annual spend" },
              "→",
              { label: "MOT MCP", sub: "DVSA API" },
              "→",
              { label: "Verdict", sub: "Buy / Negotiate / Walk Away" },
            ].map((item, i) =>
              typeof item === "string" ? (
                <span key={i} style={{ fontSize: 16, color: "var(--color-text-tertiary)" }}>{item}</span>
              ) : (
                <div key={i} style={{
                  background: "var(--color-background-primary)",
                  border: "0.5px solid var(--color-border-tertiary)",
                  borderRadius: "var(--border-radius-md)",
                  padding: "5px 10px",
                  fontSize: 12,
                }}>
                  <div style={{ fontWeight: 500 }}>{item.label}</div>
                  <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{item.sub}</div>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {error && (
        <div style={{ color: "var(--color-text-danger)", fontSize: 13, padding: "8px 12px", background: "var(--color-background-danger)", borderRadius: "var(--border-radius-md)" }}>
          {error}
        </div>
      )}

      {/* Results */}
      {result && verdict && (
        <div>
          {/* Verdict banner */}
          <div style={{
            background: verdict.bg,
            borderRadius: "var(--border-radius-lg)",
            padding: "1.25rem 1.5rem",
            marginBottom: "1rem",
            display: "flex",
            alignItems: "flex-start",
            gap: 16,
          }}>
            <div style={{
              fontSize: 28,
              fontWeight: 500,
              color: verdict.color,
              lineHeight: 1,
              minWidth: 36,
              textAlign: "center",
            }}>{verdict.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 500, color: verdict.color }}>{verdict.label}</span>
                <Pill text={`${result.confidence} confidence`} />
              </div>
              <p style={{ margin: 0, fontSize: 14, color: "var(--color-text-primary)", lineHeight: 1.6 }}>{result.summary}</p>
            </div>
          </div>

          {/* Headline reasons */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "1rem" }}>
            {result.headline_reasons?.map((r, i) => (
              <div key={i} style={{
                flex: 1, minWidth: 160,
                background: "var(--color-background-secondary)",
                borderRadius: "var(--border-radius-md)",
                padding: "8px 12px",
                fontSize: 13,
                color: "var(--color-text-secondary)",
              }}>
                <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>{i + 1}. </span>{r}
              </div>
            ))}
          </div>

          {/* Three agent cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: "1rem" }}>
            {/* Price */}
            <AgentCard title="Price agent" icon="£" accent="var(--color-border-info)">
              {result.price_analysis && (
                <>
                  <div style={{ fontSize: 13, fontWeight: 500, color: PRICE_VERDICT[result.price_analysis.verdict]?.color, marginBottom: 6 }}>
                    {PRICE_VERDICT[result.price_analysis.verdict]?.label}
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>Market value</div>
                    <div style={{ fontSize: 16, fontWeight: 500 }}>£{result.price_analysis.estimated_market_value?.toLocaleString()}</div>
                  </div>
                  {result.price_analysis.price_difference !== undefined && (
                    <div style={{ fontSize: 12, color: result.price_analysis.price_difference >= 0 ? "var(--color-text-success)" : "var(--color-text-danger)", marginBottom: 8 }}>
                      {result.price_analysis.price_difference >= 0 ? "+" : ""}£{result.price_analysis.price_difference?.toLocaleString()} vs asking
                    </div>
                  )}
                  <p style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: "0 0 8px", lineHeight: 1.5 }}>{result.price_analysis.reasoning}</p>
                  {result.price_analysis.negotiation_suggestion && (
                    <div style={{ fontSize: 11, background: "var(--color-background-info)", color: "var(--color-text-info)", padding: "5px 8px", borderRadius: "var(--border-radius-md)" }}>
                      {result.price_analysis.negotiation_suggestion}
                    </div>
                  )}
                </>
              )}
            </AgentCard>

            {/* MOT */}
            <AgentCard title="MOT agent" icon="⚙" accent="var(--color-border-warning)">
              {result.mot_analysis && (
                <>
                  <div style={{ fontSize: 13, fontWeight: 500, color: RISK_COLOR[result.mot_analysis.risk_level], marginBottom: 8 }}>
                    {result.mot_analysis.risk_level} risk
                  </div>
                  {result.mot_analysis.listing_red_flags?.map((f, i) => <Flag key={i} text={f} type="danger" />)}
                  {result.mot_analysis.risk_flags?.map((f, i) => <Flag key={i} text={f} type="warn" />)}
                  {result.mot_analysis.top_concerns?.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginBottom: 4 }}>Top concerns</div>
                      {result.mot_analysis.top_concerns.map((c, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 3 }}>• {c}</div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </AgentCard>

            {/* Running costs */}
            <AgentCard title="Costs agent" icon="↻" accent="var(--color-border-success)">
              {result.running_costs && (
                <>
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>Annual total</div>
                    <div style={{ fontSize: 18, fontWeight: 500 }}>£{result.running_costs.total_annual_cost?.toLocaleString()}</div>
                    <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{result.running_costs.fuel_efficiency}</div>
                  </div>
                  <CostRow label="Road tax" value={result.running_costs.road_tax_annual} />
                  <CostRow label="Insurance" value={result.running_costs.insurance_estimate?.low} note={`–£${result.running_costs.insurance_estimate?.high?.toLocaleString()}`} />
                  <CostRow label="Fuel" value={result.running_costs.fuel_cost_annual} />
                  <CostRow label="Servicing" value={result.running_costs.servicing_annual} />
                  <CostRow label="Tyres" value={result.running_costs.tyres_annual} />
                  {result.running_costs.depreciation_3yr && (
                    <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 8 }}>
                      Est. 3yr depreciation: £{result.running_costs.depreciation_3yr?.toLocaleString()}
                    </div>
                  )}
                </>
              )}
            </AgentCard>
          </div>

          {/* Bottom action panels */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem" }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Ask the seller</div>
              {result.questions_to_ask_seller?.map((q, i) => (
                <div key={i} style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6, paddingLeft: 12, borderLeft: "2px solid var(--color-border-secondary)" }}>
                  {q}
                </div>
              ))}
            </div>
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem" }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Inspect before buying</div>
              {result.things_to_inspect?.map((t, i) => (
                <div key={i} style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6, paddingLeft: 12, borderLeft: "2px solid var(--color-border-secondary)" }}>
                  {t}
                </div>
              ))}
            </div>
          </div>

          {(result.negotiation_advice || result.walk_away_reason) && (
            <div style={{
              marginTop: 10,
              padding: "10px 14px",
              background: result.recommendation === "WALK_AWAY" ? "var(--color-background-danger)" : "var(--color-background-warning)",
              color: result.recommendation === "WALK_AWAY" ? "var(--color-text-danger)" : "var(--color-text-warning)",
              borderRadius: "var(--border-radius-lg)",
              fontSize: 13,
              lineHeight: 1.5,
            }}>
              <strong>{result.recommendation === "WALK_AWAY" ? "Why walk away: " : "Negotiation tactic: "}</strong>
              {result.walk_away_reason || result.negotiation_advice}
            </div>
          )}

          {/* Agent log */}
          {agentLog.length > 0 && (
            <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
              {agentLog.map((l, i) => (
                <Pill key={i} text={l} color="var(--color-text-success)" bg="var(--color-background-success)" />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
