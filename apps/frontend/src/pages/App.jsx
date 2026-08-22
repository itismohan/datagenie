import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_DATAGENIE_API_BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN = import.meta.env.VITE_DATAGENIE_ACCESS_TOKEN || "";
const TENANT_LABEL = import.meta.env.VITE_DATAGENIE_TENANT_LABEL || "Northstar Analytics";

const navItems = [
  { id: "overview", label: "Control center", icon: "▦", description: "Coverage and priorities" },
  { id: "catalog", label: "Catalog", icon: "⌕", description: "Governed discovery" },
  { id: "quality", label: "Quality", icon: "◌", description: "Evidence and incidents" },
  { id: "lineage", label: "Lineage", icon: "⌘", description: "Impact and confidence" },
  { id: "proposals", label: "Proposal inbox", icon: "◈", description: "Steward review" },
  { id: "admin", label: "Administration", icon: "⚙", description: "Controls and support" },
];

const fallbackAssets = [
  {
    id: "asset-payments-fact",
    name: "payments_fact",
    qualifiedName: "warehouse.finance.payments_fact",
    type: "Table",
    domain: "Finance",
    owner: "Maya Chen",
    classification: "Confidential",
    certification: "Certified",
    quality: 96,
    freshness: "12 min ago",
    status: "Healthy",
    description: "Daily payment settlement facts used by finance and reconciliation reporting.",
    tags: ["payments", "revenue", "critical"],
    columns: 42,
    consumers: 18,
  },
  {
    id: "asset-customer-360",
    name: "customer_360",
    qualifiedName: "lakehouse.gold.customer_360",
    type: "View",
    domain: "Growth",
    owner: "Alex Rivera",
    classification: "Restricted",
    certification: "Under review",
    quality: 88,
    freshness: "48 min ago",
    status: "Review needed",
    description: "Curated customer profile used by lifecycle marketing and account intelligence teams.",
    tags: ["customer", "pii", "gold"],
    columns: 28,
    consumers: 9,
  },
  {
    id: "asset-inventory-snapshot",
    name: "inventory_snapshot",
    qualifiedName: "warehouse.operations.inventory_snapshot",
    type: "Table",
    domain: "Operations",
    owner: "Priya Nair",
    classification: "Internal",
    certification: "Certified",
    quality: 92,
    freshness: "2 h ago",
    status: "Healthy",
    description: "Hourly inventory availability snapshot with warehouse and fulfillment context.",
    tags: ["inventory", "supply-chain"],
    columns: 31,
    consumers: 12,
  },
  {
    id: "asset-risk-exposure",
    name: "risk_exposure_daily",
    qualifiedName: "warehouse.risk.risk_exposure_daily",
    type: "Table",
    domain: "Risk",
    owner: "Daniel Brooks",
    classification: "Confidential",
    certification: "Pending evidence",
    quality: 76,
    freshness: "1 d ago",
    status: "Attention",
    description: "Daily exposure aggregation with data quality and source-coverage evidence.",
    tags: ["risk", "exposure", "critical"],
    columns: 19,
    consumers: 6,
  },
];

const proposals = [
  {
    id: "prop-1048",
    title: "Clarify settlement definition",
    asset: "payments_fact",
    source: "MCP · Enterprise governed host",
    model: "approved-model",
    impact: "Metadata-only description and tags",
    evidence: "Glossary: Payments settlement",
    policy: "Allow with steward review",
    status: "Pending review",
    age: "18 min ago",
  },
  {
    id: "prop-1047",
    title: "Request certification evidence refresh",
    asset: "customer_360",
    source: "Analyst workflow",
    model: "Human initiated",
    impact: "Certification review request only",
    evidence: "Quality evidence age: 8 days",
    policy: "Requires human approval",
    status: "Pending review",
    age: "46 min ago",
  },
  {
    id: "prop-1043",
    title: "Schedule completeness check",
    asset: "risk_exposure_daily",
    source: "MCP · Enterprise governed host",
    model: "approved-model",
    impact: "Quality schedule request only",
    evidence: "Rule coverage: 4 of 6",
    policy: "Allow with obligations",
    status: "Pending review",
    age: "2 h ago",
  },
];

function requestId() {
  return `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeAsset(asset, index) {
  return {
    id: asset.id || `asset-${index}`,
    name: asset.name || asset.qualified_name || `Untitled asset ${index + 1}`,
    qualifiedName: asset.qualified_name || asset.name || "Governed asset",
    type: asset.asset_type || asset.type || "Asset",
    domain: asset.domain || "Unassigned",
    owner: asset.owner || "Owner not assigned",
    classification: asset.classification || "Not classified",
    certification: asset.certification_status || asset.lifecycle_status || "Under review",
    quality: Number(asset.quality_score ?? asset.technical_quality_score ?? 0),
    freshness: asset.quality_explainable_at ? new Date(asset.quality_explainable_at).toLocaleString() : "Evidence pending",
    status: asset.quality_score >= 90 ? "Healthy" : "Review needed",
    description: asset.description || "No stewarded description has been recorded yet.",
    tags: Array.isArray(asset.tags) ? asset.tags : [],
    columns: asset.column_count || asset.columns?.length || 0,
    consumers: asset.consumer_count || 0,
  };
}

function StatusPill({ children, tone = "neutral" }) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}

function MetricCard({ label, value, delta, tone = "brand", detail }) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span>{label}</span>
        <span className={`metric-icon metric-icon--${tone}`}>↗</span>
      </div>
      <strong>{value}</strong>
      <div className="metric-card__footer">
        <span className={delta.startsWith("+") ? "positive" : "muted"}>{delta}</span>
        <span>{detail}</span>
      </div>
    </article>
  );
}

function WorkspaceHeader({ eyebrow, title, description, action }) {
  return (
    <div className="workspace-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="workspace-header__description">{description}</p>
      </div>
      {action}
    </div>
  );
}

function Overview({ onNavigate }) {
  return (
    <div className="workspace-stack">
      <WorkspaceHeader
        eyebrow="Governance cockpit"
        title="Good morning, Maya"
        description="Your data estate is healthy overall. Three stewardship decisions need attention today."
        action={<button className="button button--primary" onClick={() => onNavigate("proposals")}>Review proposals <span>→</span></button>}
      />
      <section className="metrics-grid" aria-label="Governance coverage metrics">
        <MetricCard label="Governed assets" value="12,486" delta="+8.4%" detail="vs. last month" />
        <MetricCard label="Critical assets with fresh quality" value="91.2%" delta="+3.1 pts" detail="last 30 days" tone="success" />
        <MetricCard label="Stewardship coverage" value="84.6%" delta="+5.8 pts" detail="owner + description" tone="warning" />
        <MetricCard label="Pending decisions" value="18" delta="6 high priority" detail="human review required" tone="danger" />
      </section>
      <section className="dashboard-grid">
        <article className="panel panel--wide">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Coverage momentum</p>
              <h2>Priority asset readiness</h2>
            </div>
            <button className="button button--quiet" onClick={() => onNavigate("catalog")}>Explore catalog</button>
          </div>
          <div className="chart-shell" aria-label="Metadata coverage trend">
            <div className="chart-y-labels"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
            <div className="chart-plot">
              <div className="gridline gridline--one" /><div className="gridline gridline--two" /><div className="gridline gridline--three" /><div className="gridline gridline--four" />
              <svg viewBox="0 0 800 250" role="img" aria-label="Coverage trend rising from 58 to 85 percent" preserveAspectRatio="none">
                <defs><linearGradient id="coverage-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#536dfe" stopOpacity=".3"/><stop offset="100%" stopColor="#536dfe" stopOpacity="0"/></linearGradient></defs>
                <path d="M0 190 C55 170 75 180 120 160 S190 128 236 140 S300 108 344 118 S410 86 458 98 S525 65 570 74 S640 40 690 54 S755 28 800 32 L800 250 L0 250 Z" fill="url(#coverage-fill)" />
                <path d="M0 190 C55 170 75 180 120 160 S190 128 236 140 S300 108 344 118 S410 86 458 98 S525 65 570 74 S640 40 690 54 S755 28 800 32" fill="none" stroke="#536dfe" strokeWidth="4" strokeLinecap="round" />
              </svg>
              <div className="chart-months"><span>Jan</span><span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span><span>Jul</span></div>
            </div>
          </div>
          <div className="chart-summary"><span><i className="dot dot--brand" /> Usable description, owner, classification and freshness</span><strong>85.1%</strong></div>
        </article>
        <article className="panel attention-panel">
          <div className="panel-heading"><div><p className="panel-kicker">Needs attention</p><h2>Stewardship queue</h2></div><span className="count-badge">18</span></div>
          <div className="attention-list">
            <button className="attention-item" onClick={() => onNavigate("proposals")}><span className="attention-icon attention-icon--warning">!</span><span><strong>6 proposals need review</strong><small>Evidence and impact are ready for stewards</small></span><span>→</span></button>
            <button className="attention-item" onClick={() => onNavigate("quality")}><span className="attention-icon attention-icon--danger">◌</span><span><strong>3 critical assets have stale evidence</strong><small>Refresh explainable quality before use</small></span><span>→</span></button>
            <button className="attention-item" onClick={() => onNavigate("catalog")}><span className="attention-icon attention-icon--brand">◇</span><span><strong>9 assets need an accountable owner</strong><small>Route ownership through governance workflow</small></span><span>→</span></button>
          </div>
        </article>
      </section>
      <section className="dashboard-grid dashboard-grid--secondary">
        <article className="panel">
          <div className="panel-heading"><div><p className="panel-kicker">Operational confidence</p><h2>Quality posture</h2></div><StatusPill tone="success">Fresh evidence</StatusPill></div>
          <div className="quality-summary"><div className="quality-score"><strong>91</strong><span>/100</span></div><div><strong>Critical estate quality</strong><p>142 of 156 critical assets have recent, explainable evidence.</p><button className="text-button" onClick={() => onNavigate("quality")}>Inspect evidence →</button></div></div>
          <div className="progress-track"><span style={{ width: "91%" }} /></div>
        </article>
        <article className="panel">
          <div className="panel-heading"><div><p className="panel-kicker">Governed activity</p><h2>Recent decisions</h2></div><button className="button button--quiet" onClick={() => onNavigate("proposals")}>View inbox</button></div>
          <div className="activity-list">
            <div><span className="activity-dot activity-dot--success"/><p><strong>Payments fact</strong> certification renewed<small>15 minutes ago · Steward review</small></p></div>
            <div><span className="activity-dot activity-dot--brand"/><p><strong>Customer 360</strong> proposal received<small>46 minutes ago · MCP-originated intent</small></p></div>
            <div><span className="activity-dot activity-dot--warning"/><p><strong>Risk exposure</strong> quality evidence aging<small>2 hours ago · Freshness obligation</small></p></div>
          </div>
        </article>
      </section>
    </div>
  );
}

function Catalog({ assets, selected, onSelect, query, setQuery, activeFacet, setActiveFacet, connection, requestId, onNavigate }) {
  const facets = ["All assets", "Certified", "Critical", "Needs owner", "Fresh quality"];
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return assets.filter((asset) => {
      const matchesQuery = !normalizedQuery || [asset.name, asset.qualifiedName, asset.domain, asset.owner, asset.classification, ...asset.tags].join(" ").toLowerCase().includes(normalizedQuery);
      const matchesFacet = activeFacet === "All assets" || (activeFacet === "Certified" && asset.certification === "Certified") || (activeFacet === "Critical" && asset.tags.includes("critical")) || (activeFacet === "Needs owner" && asset.owner === "Owner not assigned") || (activeFacet === "Fresh quality" && asset.quality >= 90);
      return matchesQuery && matchesFacet;
    });
  }, [assets, activeFacet, query]);
  return (
    <div className="workspace-stack">
      <WorkspaceHeader eyebrow="Governed discovery" title="Catalog intelligence" description="Find trusted data through ownership, classification, quality, freshness and lineage context." action={<button className="button button--primary" onClick={() => onNavigate("proposals")}>Create proposal <span>→</span></button>} />
      {connection.mode !== "live" && <div className="connection-notice"><span>◌</span><div><strong>Demonstration data is active.</strong> {connection.message} <span className="request-chip">Request ID: {requestId}</span></div></div>}
      <section className="catalog-layout">
        <div className="catalog-main">
          <div className="search-bar"><span aria-hidden="true">⌕</span><input aria-label="Search governed assets" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search assets, business terms, owners, domains or tags" /><kbd>⌘ K</kbd></div>
          <div className="facet-row" aria-label="Catalog filters">{facets.map((facet) => <button key={facet} className={`facet ${activeFacet === facet ? "facet--active" : ""}`} onClick={() => setActiveFacet(facet)}>{facet}</button>)}</div>
          <div className="table-card">
            <div className="table-toolbar"><span>{filtered.length} governed assets</span><span>Ranked by trust, relevance and recency</span></div>
            <div className="catalog-table-wrap"><table className="catalog-table"><thead><tr><th>Asset</th><th>Domain</th><th>Owner</th><th>Trust posture</th><th>Freshness</th></tr></thead><tbody>{filtered.map((asset) => <tr key={asset.id} onClick={() => onSelect(asset)} className={selected?.id === asset.id ? "is-selected" : ""}><td><div className="asset-cell"><span className="asset-type-icon">{asset.type === "View" ? "◇" : "▤"}</span><div><strong>{asset.name}</strong><small>{asset.qualifiedName}</small></div></div></td><td><StatusPill tone="neutral">{asset.domain}</StatusPill></td><td>{asset.owner}</td><td><div className="trust-cell"><StatusPill tone={asset.certification === "Certified" ? "success" : "warning"}>{asset.certification}</StatusPill><span>{asset.quality || "—"} quality</span></div></td><td>{asset.freshness}</td></tr>)}</tbody></table></div>
          </div>
        </div>
        <AssetDetail asset={selected} onNavigate={onNavigate} />
      </section>
    </div>
  );
}

function AssetDetail({ asset, onNavigate }) {
  if (!asset) return <aside className="detail-panel"><p className="eyebrow">Asset context</p><h2>Select an asset</h2><p>Choose a catalog result to inspect governance and evidence context.</p></aside>;
  return (
    <aside className="detail-panel" aria-label={`${asset.name} detail`}>
      <div className="detail-panel__header"><span className="asset-type-icon asset-type-icon--large">▤</span><button className="icon-button" aria-label="Close asset detail">×</button></div>
      <p className="eyebrow">{asset.domain} · {asset.type}</p><h2>{asset.name}</h2><p className="detail-description">{asset.description}</p>
      <div className="tag-row">{asset.tags.map((tag) => <span key={tag} className="tag">{tag}</span>)}</div>
      <div className="detail-section"><h3>Trust posture</h3><div className="detail-status-grid"><div><small>Certification</small><StatusPill tone={asset.certification === "Certified" ? "success" : "warning"}>{asset.certification}</StatusPill></div><div><small>Classification</small><StatusPill tone={asset.classification === "Internal" ? "neutral" : "danger"}>{asset.classification}</StatusPill></div><div><small>Quality evidence</small><strong>{asset.quality || "—"}/100</strong></div><div><small>Freshness</small><strong>{asset.freshness}</strong></div></div></div>
      <div className="detail-section"><h3>Accountability</h3><div className="owner-card"><span className="avatar avatar--small">{asset.owner.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span><div><strong>{asset.owner}</strong><small>Data owner · {asset.columns} columns · {asset.consumers} consumers</small></div></div></div>
      <div className="detail-section"><h3>Evidence trail</h3><div className="evidence-line"><span>✓</span><p><strong>Technical metadata harvested</strong><small>Version 42 · source verified</small></p></div><div className="evidence-line"><span>◌</span><p><strong>Quality rule suite is explainable</strong><small>6 active rules · latest run available</small></p></div><div className="evidence-line"><span>⌘</span><p><strong>Lineage impact is bounded</strong><small>12 downstream consumers · confidence 0.93</small></p></div></div>
      <div className="detail-actions"><button className="button button--secondary" onClick={() => onNavigate("lineage")}>Analyze lineage</button><button className="button button--primary" onClick={() => onNavigate("proposals")}>Propose change</button></div>
    </aside>
  );
}

function QualityWorkspace() {
  const rules = [{ name: "Completeness", value: 98, state: "Healthy", tone: "success" }, { name: "Uniqueness", value: 95, state: "Healthy", tone: "success" }, { name: "Validity", value: 87, state: "Watch", tone: "warning" }, { name: "Freshness", value: 91, state: "Healthy", tone: "success" }];
  return <div className="workspace-stack"><WorkspaceHeader eyebrow="Explainable quality" title="Quality evidence" description="Scores are useful only with rule context, freshness and accountable remediation." action={<button className="button button--primary">Review incidents <span>→</span></button>} /><section className="metrics-grid"><MetricCard label="Critical coverage" value="91.2%" delta="+3.1 pts" detail="fresh evidence" tone="success"/><MetricCard label="Open incidents" value="7" delta="2 high severity" detail="accountable owners" tone="danger"/><MetricCard label="Rules monitored" value="1,284" delta="+66" detail="versioned checks"/><MetricCard label="Evidence freshness" value="6.4 d" delta="Within policy" detail="median age" tone="success"/></section><section className="dashboard-grid"><article className="panel panel--wide"><div className="panel-heading"><div><p className="panel-kicker">payments_fact</p><h2>Rule evidence at a glance</h2></div><StatusPill tone="success">Fresh · 12 min ago</StatusPill></div><div className="rule-list">{rules.map((rule) => <div className="rule-row" key={rule.name}><div><strong>{rule.name}</strong><small>Rule version 3.4 · Threshold 90%</small></div><div className="rule-meter"><span style={{ width: `${rule.value}%` }} /></div><strong>{rule.value}%</strong><StatusPill tone={rule.tone}>{rule.state}</StatusPill></div>)}</div><div className="evidence-callout"><span>i</span><p><strong>How to read this score.</strong> 96/100 combines technical quality evidence only. It does not certify business fitness or override governance obligations.</p></div></article><article className="panel"><div className="panel-heading"><div><p className="panel-kicker">Remediation</p><h2>Active incidents</h2></div><span className="count-badge count-badge--danger">7</span></div><div className="incident-list"><div><StatusPill tone="danger">High</StatusPill><p><strong>Risk exposure freshness</strong><small>Owner: Daniel Brooks · opened 2h ago</small></p></div><div><StatusPill tone="warning">Medium</StatusPill><p><strong>Customer 360 validity drift</strong><small>Owner: Alex Rivera · evidence attached</small></p></div><div><StatusPill tone="warning">Medium</StatusPill><p><strong>Inventory referential integrity</strong><small>Owner: Priya Nair · review pending</small></p></div></div></article></section></div>;
}

function LineageWorkspace() {
  return <div className="workspace-stack"><WorkspaceHeader eyebrow="Operational impact" title="Lineage intelligence" description="Trace bounded upstream and downstream relationships with confidence and accountable consumers." action={<button className="button button--primary">Run impact review <span>→</span></button>} /><section className="lineage-layout"><article className="panel lineage-canvas"><div className="panel-heading"><div><p className="panel-kicker">payments_fact</p><h2>Downstream impact</h2></div><div className="segmented"><button className="is-active">Downstream</button><button>Upstream</button></div></div><div className="lineage-graph" role="img" aria-label="Bounded downstream lineage from payment fact to finance reporting and executive metrics"><div className="lineage-node lineage-node--source"><span>▤</span><strong>payments_fact</strong><small>Certified table</small></div><div className="lineage-connector lineage-connector--one"/><div className="lineage-connector lineage-connector--two"/><div className="lineage-connector lineage-connector--three"/><div className="lineage-node lineage-node--consumer lineage-node--one"><span>▤</span><strong>revenue_daily</strong><small>Transformation</small></div><div className="lineage-node lineage-node--consumer lineage-node--two"><span>▤</span><strong>settlement_ops</strong><small>Operational view</small></div><div className="lineage-node lineage-node--consumer lineage-node--three"><span>▦</span><strong>Executive finance</strong><small>Dashboard</small></div></div><div className="lineage-footer"><span><i className="dot dot--success"/> Confidence 0.93</span><span>Depth 2 of 3 · 12 nodes returned</span><span>Last observed 8 min ago</span></div></article><aside className="panel impact-panel"><p className="panel-kicker">Impact summary</p><h2>18 consumers may be affected</h2><p>Changing the asset schema requires review by Finance Analytics and Settlement Operations owners.</p><div className="impact-stat"><strong>3</strong><span>Critical reports</span></div><div className="impact-stat"><strong>2</strong><span>Owned domains</span></div><div className="impact-stat"><strong>0</strong><span>Unresolved lineage breaks</span></div><div className="evidence-callout"><span>i</span><p>This view is bounded to approved lineage sources. Missing relationships are not evidence of no impact.</p></div></aside></section></div>;
}

function ProposalsWorkspace() {
  return <div className="workspace-stack"><WorkspaceHeader eyebrow="Human-in-the-loop governance" title="Proposal inbox" description="Review evidence-bearing intent. A proposal does not change a governed resource until an authorized steward approves and confirms it in the secure workflow." action={<a className="button button--primary" href="/api/v1/governance/inbox">Open steward inbox <span>→</span></a>} /><div className="governance-banner"><span>◈</span><div><strong>Proposal-only boundary</strong><p>MCP and AI hosts can create reviewable proposals. They cannot approve, execute, certify, or directly mutate governed resources.</p></div><StatusPill tone="warning">Human review required</StatusPill></div><section className="proposal-grid">{proposals.map((proposal) => <article className="proposal-card" key={proposal.id}><div className="proposal-card__top"><StatusPill tone="warning">{proposal.status}</StatusPill><small>{proposal.age}</small></div><h2>{proposal.title}</h2><p className="proposal-asset">{proposal.asset}</p><div className="proposal-meta"><div><small>Source</small><strong>{proposal.source}</strong></div><div><small>Policy result</small><strong>{proposal.policy}</strong></div><div><small>Evidence</small><strong>{proposal.evidence}</strong></div><div><small>Impact</small><strong>{proposal.impact}</strong></div></div><div className="proposal-footer"><span className="model-label">{proposal.model}</span><a href="/api/v1/governance/inbox" className="text-button">View evidence and review route →</a></div></article>)}</section><div className="panel proposal-note"><span>i</span><p><strong>Confirmation remains server-bound.</strong> The secure steward inbox issues any confirmation nonce only after approval. This workspace deliberately never displays or submits one.</p></div></div>;
}

function AdminWorkspace({ requestId, connection }) {
  return <div className="workspace-stack"><WorkspaceHeader eyebrow="Tenant controls" title="Administration posture" description="Understand data governance controls, integration readiness, and safe support correlation without exposing secrets." action={<button className="button button--primary">Manage integrations <span>→</span></button>} /><section className="admin-grid"><article className="panel"><div className="panel-heading"><div><p className="panel-kicker">Tenant context</p><h2>{TENANT_LABEL}</h2></div><StatusPill tone="success">Protected</StatusPill></div><div className="admin-list"><div><span>Tenant isolation</span><strong>Database RLS enforced</strong></div><div><span>Roles and policy</span><strong>Deterministic evaluation</strong></div><div><span>Audit boundary</span><strong>Tenant-scoped evidence</strong></div><div><span>Environment</span><strong>{connection.mode === "live" ? "Connected" : "Local demonstration"}</strong></div></div></article><article className="panel"><div className="panel-heading"><div><p className="panel-kicker">MCP ecosystem</p><h2>Integration readiness</h2></div><StatusPill tone="brand">Internal beta</StatusPill></div><div className="admin-list"><div><span>Approved surface</span><strong>4 discovery + 3 proposal-intent tools</strong></div><div><span>Proposal control</span><strong>Steward inbox and confirmation rechecks</strong></div><div><span>Partner evidence</span><strong>Synthetic preflight available</strong></div><div><span>Host onboarding</span><strong>Tenant-admin pack published</strong></div></div><button className="text-button">View MCP onboarding materials →</button></article><article className="panel panel--full"><div className="panel-heading"><div><p className="panel-kicker">Support correlation</p><h2>Latest catalog request</h2></div><StatusPill tone={connection.mode === "live" ? "success" : "neutral"}>{connection.mode === "live" ? "API connected" : "Demo mode"}</StatusPill></div><div className="support-card"><div><small>Request ID</small><code>{requestId}</code></div><div><small>Safe support intake</small><p>Share request ID, tenant label, workspace, timestamp and safe error code. Do not share tokens, client secrets, source credentials, raw rows, prompts, or confirmation nonces.</p></div><button className="button button--secondary" onClick={() => navigator.clipboard?.writeText(requestId)}>Copy request ID</button></div></article></section></div>;
}

export default function App() {
  const [activeWorkspace, setActiveWorkspace] = useState("overview");
  const [assets, setAssets] = useState(fallbackAssets);
  const [selectedAsset, setSelectedAsset] = useState(fallbackAssets[0]);
  const [query, setQuery] = useState("");
  const [activeFacet, setActiveFacet] = useState("All assets");
  const [requestIdState, setRequestIdState] = useState(requestId());
  const [connection, setConnection] = useState({ mode: "loading", message: "Connecting to governed catalog…" });
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const correlationId = requestId();
    setRequestIdState(correlationId);
    const headers = { Accept: "application/json", "X-Request-ID": correlationId };
    if (ACCESS_TOKEN) headers.Authorization = `Bearer ${ACCESS_TOKEN}`;
    fetch(`${API_BASE_URL}/api/v1/assets?limit=50`, { headers, signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload?.error?.message || "The governed catalog could not be loaded.");
        const rawAssets = Array.isArray(payload) ? payload : payload.items;
        if (!Array.isArray(rawAssets)) throw new Error("The catalog response did not contain an asset list.");
        const normalizedAssets = rawAssets.map(normalizeAsset);
        setAssets(normalizedAssets.length ? normalizedAssets : fallbackAssets);
        setSelectedAsset(normalizedAssets[0] || fallbackAssets[0]);
        setConnection({ mode: "live", message: `Live governed catalog loaded from ${API_BASE_URL}.` });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setAssets(fallbackAssets);
        setSelectedAsset(fallbackAssets[0]);
        setConnection({ mode: "demo", message: "The catalog API is unavailable or requires an authenticated runtime token. These are synthetic demonstration assets, not tenant evidence." });
      });
    return () => controller.abort();
  }, []);

  const navigate = (workspace) => { setActiveWorkspace(workspace); setNavigationOpen(false); };
  const workspace = {
    overview: <Overview onNavigate={navigate} />,
    catalog: <Catalog assets={assets} selected={selectedAsset} onSelect={setSelectedAsset} query={query} setQuery={setQuery} activeFacet={activeFacet} setActiveFacet={setActiveFacet} connection={connection} requestId={requestIdState} onNavigate={navigate} />,
    quality: <QualityWorkspace />,
    lineage: <LineageWorkspace />,
    proposals: <ProposalsWorkspace />,
    admin: <AdminWorkspace requestId={requestIdState} connection={connection} />,
  }[activeWorkspace];

  return <div className="app-shell"><aside className={`sidebar ${navigationOpen ? "sidebar--open" : ""}`}><div className="brand"><div className="brand-mark"><span>✦</span></div><div><strong>DataGenie</strong><small>Governed intelligence</small></div><button className="mobile-close" aria-label="Close navigation" onClick={() => setNavigationOpen(false)}>×</button></div><div className="tenant-card"><span className="tenant-icon">◈</span><div><small>Active tenant</small><strong>{TENANT_LABEL}</strong></div><span className="tenant-chevron">⌄</span></div><nav aria-label="Primary navigation">{navItems.map((item) => <button key={item.id} className={`nav-item ${activeWorkspace === item.id ? "nav-item--active" : ""}`} onClick={() => navigate(item.id)}><span>{item.icon}</span><div><strong>{item.label}</strong><small>{item.description}</small></div></button>)}</nav><div className="sidebar-footer"><div className="support-mini"><span>?</span><div><strong>Need support?</strong><small>Use request ID correlation</small></div></div><button className="help-link">Open help center ↗</button></div></aside><main className="main-stage"><header className="topbar"><div className="topbar__left"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setNavigationOpen(true)}>☰</button><div className="crumbs"><span>DataGenie</span><span>/</span><strong>{navItems.find((item) => item.id === activeWorkspace)?.label}</strong></div></div><div className="topbar__right"><button className="top-icon-button" aria-label="Open global search" onClick={() => navigate("catalog")}>⌕</button><div className="notification-wrap"><button className="top-icon-button notification-button" aria-label="Open notifications" onClick={() => setNotificationsOpen(!notificationsOpen)}>♢<i /></button>{notificationsOpen && <div className="notification-popover"><strong>Attention queue</strong><p>6 proposals and 3 quality items need steward attention.</p><button className="text-button" onClick={() => navigate("proposals")}>Review queue →</button></div>}</div><button className="profile-button" aria-label="Open user menu"><span className="avatar">MC</span><span className="profile-copy"><strong>Maya Chen</strong><small>Data steward</small></span><span>⌄</span></button></div></header><div className="workspace">{workspace}</div></main>{navigationOpen && <button className="sidebar-scrim" aria-label="Close navigation overlay" onClick={() => setNavigationOpen(false)} />}</div>;
}
