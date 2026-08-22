/**
 * DataGenie Trust Fabric: public product and documentation site.
 * Design philosophy: editorial enterprise modernism; evidence-forward, asymmetric, and deliberately restrained.
 */
import { useState } from "react";
import "./market-comparison.css";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Code2,
  Database,
  FileSearch,
  GitBranch,
  Layers3,
  LockKeyhole,
  Menu,
  Route,
  ShieldCheck,
  Sparkles,
  UsersRound,
  X,
} from "lucide-react";

const LOGO_URL = `${import.meta.env.BASE_URL}datagenie.png`;

const navItems = [
  ["Platform", "#platform"],
  ["Architecture", "#architecture"],
  ["Governance model", "#governance"],
];

const productPillars = [
  {
    icon: Database,
    number: "01",
    title: "Catalog the estate",
    body: "Turn sources, schemas, tables, views and columns into a searchable, governed map of the data your business depends on.",
    evidence: "Stable identifiers · curated metadata preserved · ownership visible",
  },
  {
    icon: Activity,
    number: "02",
    title: "Prove quality in context",
    body: "Attach explainable rules, thresholds, freshness, incidents and accountable owners to the assets that matter most.",
    evidence: "Evidence-bearing scores · versioned rules · remediation history",
  },
  {
    icon: GitBranch,
    number: "03",
    title: "Trace operational impact",
    body: "Connect sources, transformations, reports and critical consumers so a change or incident is understood before it spreads.",
    evidence: "Typed relationships · bounded confidence · downstream context",
  },
  {
    icon: ShieldCheck,
    number: "04",
    title: "Govern with people in control",
    body: "AI agents can prepare evidence-rich intent, while named stewards retain the authority to review, approve and confirm governed change.",
    evidence: "Proposal-only agents · policy rechecks · durable audit trail",
  },
];

const docs = {
  what: {
    kicker: "What DataGenie is",
    title: "A governed intelligence layer for the enterprise data estate.",
    body: "DataGenie brings together discovery, metadata, ownership, quality evidence, lineage impact, and stewardship workflow into one operational model. It does not replace your warehouses, transformation systems, or identity provider. It makes their data assets easier to find, understand, trust, and govern.",
    bullets: ["A catalog of discovered and stewarded metadata", "Explainable technical-quality evidence and remediation tracking", "Lineage and impact context that stays connected to ownership and governance", "Proposal-based assistance that preserves human decision authority"],
  },
  why: {
    kicker: "Why it matters",
    title: "Reliable data decisions need more than a searchable list of tables.",
    body: "Enterprise teams face a gap between what exists in data platforms and what people can safely use. DataGenie closes that gap with evidence: who owns an asset, how it is classified, when its quality was last proven, what depends on it, and what policy obligations apply.",
    bullets: ["Reduce time from source connection to trusted discovery", "Give data stewards a reviewable, auditable decision surface", "Make quality and lineage operational instead of ornamental", "Keep agents useful without letting them bypass governance"],
  },
  how: {
    kicker: "How it works",
    title: "A connected control plane, not a collection of ungoverned automations.",
    body: "Connectors discover metadata and publish durable job history. Policy checks evaluate tenant, role, classification, lifecycle and evidence conditions. Catalog, quality and lineage context travel with the asset. Agents produce structured proposal intent; the steward inbox separates a recommendation from a governed change.",
    bullets: ["Connect → discover → normalize → steward", "Search → inspect policy/evidence → assess impact", "Propose → review → approve → server-confirm", "Correlate request IDs → ledger evidence → operational support"],
  },
};

function SectionMark({ children }: { children: string }) {
  return <p className="section-mark"><span className="signal-rail" aria-hidden="true"><span /></span><span className="section-line" />{children}</p>;
}

function EvidenceLine({ children }: { children: string }) {
  return <p className="evidence-line"><CheckCircle2 size={15} />{children}</p>;
}

function AssetDossierVisual() {
  return <div className="asset-dossier" role="img" aria-label="Example governed asset record with ownership, classification, freshness and quality evidence">
    <div className="dossier-chrome"><span className="dossier-kicker">Governed asset dossier</span><span className="dossier-status">CURRENT</span></div>
    <div className="dossier-title"><Database size={19} /><div><strong>finance.settlement_facts</strong><span>Production · trusted data product</span></div></div>
    <div className="dossier-grid"><div><span>Accountable owner</span><strong>Finance Operations</strong></div><div><span>Classification</span><strong>Confidential</strong></div><div><span>Freshness evidence</span><strong>14 min ago</strong></div><div><span>Quality signal</span><strong className="is-healthy">98.6% explained</strong></div></div>
    <div className="dossier-footer"><span>metadata v42</span><span>● evidence attached</span></div>
  </div>;
}

function ProposalBoundaryVisual() {
  return <div className="proposal-visual" role="img" aria-label="Proposal workflow from agent intent through steward review and server confirmation">
    <div className="proposal-node proposal-node--agent"><span>01</span><strong>Agent intent</strong><small>Evidence + diff</small></div>
    <div className="proposal-arrow" aria-hidden="true">→</div>
    <div className="proposal-node proposal-node--inbox"><span>02</span><strong>Steward inbox</strong><small>Human decision</small></div>
    <div className="proposal-arrow" aria-hidden="true">→</div>
    <div className="proposal-node proposal-node--server"><span>03</span><strong>Server confirm</strong><small>Hash + nonce + policy</small></div>
    <div className="proposal-boundary"><LockKeyhole size={15} /><span>authority boundary</span></div>
  </div>;
}

function LineageFlowVisual() {
  return <div className="lineage-flow" role="img" aria-label="Sample data lineage flow from source systems through transformations to business reports">
    <div className="lineage-flow-head"><span>Example data flow</span><span>Confidence: bounded</span></div>
    <div className="lineage-lanes">
      <div className="lineage-stage lineage-stage--source"><span className="stage-label">Sources</span><strong>PostgreSQL</strong><strong>Snowflake</strong></div>
      <div className="lineage-connector" aria-hidden="true">→</div>
      <div className="lineage-stage lineage-stage--transform"><span className="stage-label">Transform</span><strong>dbt model</strong><small>settlement_rollup</small></div>
      <div className="lineage-connector" aria-hidden="true">→</div>
      <div className="lineage-stage lineage-stage--product"><span className="stage-label">Data product</span><strong>Finance metrics</strong><small>quality monitored</small></div>
      <div className="lineage-connector" aria-hidden="true">→</div>
      <div className="lineage-stage lineage-stage--consumer"><span className="stage-label">Consumers</span><strong>Executive dashboard</strong><strong>Risk report</strong></div>
    </div>
    <div className="lineage-observation"><Activity size={15} /><span>Quality incident here?</span><strong>See 2 reports and 12 downstream consumers</strong></div>
  </div>;
}

function ArchitectureFlowVisual() {
  return <div className="architecture-flow" role="img" aria-label="DataGenie quick-start architecture showing sources through connector workers, the catalog governance boundary, evidence and lineage, and governed discovery">
    <div className="architecture-flow-head"><span>Quick-start architecture</span><span>Metadata forward · authority bounded</span></div>
    <div className="architecture-track">
      <div className="architecture-node architecture-node--sources"><span>01</span><strong>Enterprise sources</strong><small>PostgreSQL · Snowflake · transformation tools</small></div>
      <div className="architecture-arrow" aria-hidden="true">→</div>
      <div className="architecture-node architecture-node--ingest"><span>02</span><strong>Connector workers</strong><small>Discover · profile · incrementally sync</small></div>
      <div className="architecture-arrow" aria-hidden="true">→</div>
      <div className="architecture-node architecture-node--catalog"><span>03</span><strong>Catalog control plane</strong><small>Tenant · policy · audit · metadata</small></div>
      <div className="architecture-arrow" aria-hidden="true">→</div>
      <div className="architecture-node architecture-node--outcome"><span>04</span><strong>Governed discovery</strong><small>Search · evidence · impact · MCP</small></div>
    </div>
    <div className="architecture-evidence"><div><Activity size={15} /><span><strong>Quality evidence</strong>Rules, runs and incidents stay attached to the asset.</span></div><div><Route size={15} /><span><strong>Operational lineage</strong>Source → transform → product → consumer context.</span></div><div><LockKeyhole size={15} /><span><strong>Steward authority</strong>Proposals are reviewed before a server-confirmed change.</span></div></div>
  </div>;
}

const radarAxes = ["Agent change control", "Open-source flexibility", "Packaged breadth", "Cloud ecosystem fit", "Developer extensibility"];
const radarProfiles = [
  { label: "DataGenie", color: "#6778ff", values: [5, 5, 2, 2, 5] },
  { label: "Enterprise suites", color: "#37bda2", values: [3, 1, 5, 5, 3] },
  { label: "Open metadata platforms", color: "#d8a455", values: [2, 5, 3, 3, 5] },
];

function radarPoint(value: number, index: number, radius = 104) {
  const angle = (Math.PI * 2 * index) / radarAxes.length - Math.PI / 2;
  const distance = (value / 5) * radius;
  return [160 + Math.cos(angle) * distance, 160 + Math.sin(angle) * distance];
}

function radarPolygon(values: number[]) {
  return values.map((value, index) => radarPoint(value, index).join(",")).join(" ");
}

function MarketComparisonVisual() {
  return <div className="market-radar" role="img" aria-label="Directional market-positioning radar comparing DataGenie, enterprise governance suites, and open metadata platforms">
    <svg viewBox="0 0 320 320" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((ring) => <polygon key={ring} className="radar-ring" points={radarAxes.map((_, index) => radarPoint(ring, index).join(",")).join(" ")} />)}
      {radarAxes.map((_, index) => { const [x, y] = radarPoint(5, index); return <line key={index} className="radar-axis" x1="160" y1="160" x2={x} y2={y} />; })}
      {radarProfiles.map((profile) => <polygon key={profile.label} className="radar-profile" style={{ "--radar-color": profile.color } as React.CSSProperties} points={radarPolygon(profile.values)} />)}
      {radarAxes.map((axis, index) => { const [x, y] = radarPoint(5.9, index); return <text key={axis} className="radar-label" x={x} y={y}>{axis}</text>; })}
    </svg>
    <div className="radar-legend">{radarProfiles.map((profile) => <span key={profile.label}><i style={{ background: profile.color }} />{profile.label}</span>)}</div>
  </div>;
}

export default function Home() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [docTab, setDocTab] = useState<keyof typeof docs>("what");
  const [flowOpen, setFlowOpen] = useState<number | null>(1);

  const activeDoc = docs[docTab];

  return (
    <div className="site-shell">
      <header className="site-header">
        <a href="#top" className="brand-lockup" aria-label="DataGenie home">
          <span className="official-logo-frame"><img src={LOGO_URL} alt="DataGenie brand illustration" /></span>
          <span className="brand-word">DataGenie</span>
          <span className="brand-divider" />
          <span className="brand-subtitle">Governed intelligence</span>
        </a>
        <nav className="desktop-nav" aria-label="Primary navigation">
          {navItems.map(([label, href]) => <a key={label} href={href}>{label}</a>)}
        </nav>
        <a className="header-cta" href="#docs">Read the model <ArrowUpRight size={15} /></a>
        <button className="menu-button" onClick={() => setMobileOpen(!mobileOpen)} aria-label={mobileOpen ? "Close navigation" : "Open navigation"}>
          {mobileOpen ? <X size={21} /> : <Menu size={21} />}
        </button>
        {mobileOpen && <div className="mobile-nav">{navItems.map(([label, href]) => <a key={label} href={href} onClick={() => setMobileOpen(false)}>{label}<ArrowRight size={15} /></a>)}</div>}
      </header>

      <main id="top">
        <section className="hero section-rail">
          <div className="hero-copy">
            <SectionMark>Data governance, made operational</SectionMark>
            <h1>Make every data decision <em>traceable.</em></h1>
            <p className="hero-lede">DataGenie connects discovery, quality, lineage and human stewardship so enterprise teams can use data with context, evidence and control.</p>
            <div className="hero-actions">
              <a href="#platform" className="button button-primary">Explore the control plane <ArrowRight size={16} /></a>
              <a href="#governance" className="button button-quiet">See the governance model <span>↓</span></a>
            </div>
            <div className="hero-proof"><EvidenceLine>Policy-aware discovery across catalog, quality and lineage</EvidenceLine><EvidenceLine>Human stewardship remains the authority for governed change</EvidenceLine></div>
          </div>
          <div className="hero-visual" aria-label="DataGenie governed intelligence constellation">
            <div className="hero-network" aria-hidden="true"><span /><span /><span /><span /><i /><i /><i /></div>
            <div className="hero-brand-emblem"><img src={LOGO_URL} alt="DataGenie AI brand mascot" /></div>
            <div className="hero-console">
              <div className="console-top"><span className="console-pulse" /><span>Governed asset context</span><code>trusted</code></div>
              <div className="console-row"><span>Owner</span><strong>Finance data stewardship</strong></div>
              <div className="console-status-grid" aria-label="Governed asset status summary"><div><span>Trust</span><strong className="console-good">Allowed</strong><small>Policy check current</small></div><div><span>Evidence</span><strong className="console-good">Fresh</strong><small>Quality confirmed</small></div><div><span>Impact</span><strong>12 users</strong><small>Consumers mapped</small></div></div>
              <div className="console-legend"><span className="proof-chip proof-chip--healthy">● healthy evidence</span><span className="proof-chip proof-chip--review">◆ review boundary</span></div>
            </div>
            <div className="hero-orbit hero-orbit-one" /><div className="hero-orbit hero-orbit-two" />
          </div>
        </section>

        <section className="signal-band" aria-label="DataGenie operating principles">
          <span>DISCOVER</span><i /> <span>TRUST</span><i /> <span>GOVERN</span><i /> <span>EMPOWER</span>
          <p>Evidence moves with the asset.</p>
        </section>

        <section id="platform" className="platform section-rail">
          <div className="section-intro"><SectionMark>The DataGenie control plane</SectionMark><h2>One operating model for data people can actually trust.</h2></div>
          <p className="section-aside">DataGenie is designed for the point where platforms, policies and people meet. It makes context usable without pretending automation can replace accountable decisions.</p>
          <div className="pillar-grid">
            {productPillars.map((pillar) => { const Icon = pillar.icon; return <article className="pillar-card" key={pillar.number}><div className="pillar-head"><span>{pillar.number}</span><Icon size={22} /></div><h3>{pillar.title}</h3><p>{pillar.body}</p><div className="card-evidence">{pillar.evidence}</div></article>; })}
          </div>
        </section>

        <section id="architecture" className="architecture section-rail">
          <div className="architecture-intro"><div><SectionMark>From source to trusted decision</SectionMark><h2>Architecture that turns data flow into <em>governed context.</em></h2></div><p>DataGenie connects source discovery, durable ingestion, the tenant-bound catalog control plane, and quality and lineage evidence so teams can see what data is, who owns it, and what a change will affect.</p></div>
          <ArchitectureFlowVisual />
          <p className="architecture-note"><LockKeyhole size={17} /><span><strong>Bounded authority:</strong> metadata and evidence move through the platform, but governance changes remain proposal-only until an authorized steward and server-side rechecks confirm them.</span></p>
        </section>

        <section id="comparison" className="market-compare section-rail">
          <div className="market-compare-intro"><div><SectionMark>Market positioning</SectionMark><h2>Choose a control plane when <em>governance has to be provable.</em></h2></div><p>DataGenie is intentionally not presented as a feature-for-feature replacement for every established suite. It is a focused, open control plane for tenant-bound discovery and agent-assisted governance that remains accountable to a human steward.</p></div>
          <div className="market-compare-grid"><MarketComparisonVisual /><div className="market-principles"><div><span>01</span><strong>Policy is executable</strong><p>Deterministic rules return an observable decision, rule references and obligations—not a black-box recommendation.</p></div><div><span>02</span><strong>Agents cannot self-approve</strong><p>MCP tools create pending intent only; a current steward and server-side rechecks remain the mutation boundary.</p></div><div><span>03</span><strong>Evidence is operational</strong><p>Tenant, host, request ID, policy outcome and execution result correlate in a durable support ledger.</p></div></div></div>
          <div className="market-matrix-wrap"><table className="market-matrix"><caption>Feature matrix: architectural emphasis, not a benchmark score</caption><thead><tr><th>Decision dimension</th><th>DataGenie</th><th>Enterprise suites</th><th>Microsoft Purview</th><th>Open metadata platforms</th></tr></thead><tbody><tr><th>Agent-initiated governance change</th><td><strong>Proposal-only</strong><br /><span>Hash, nonce, steward, rechecks</span></td><td>Vendor workflow dependent</td><td>Service workflow dependent</td><td>Implementation dependent</td></tr><tr><th>MCP request security evidence</th><td><strong>Tenant + host + request ledger</strong><br /><span>Scope and outcome correlated</span></td><td>Verify per product and configuration</td><td>Verify per service and configuration</td><td>Verify per deployment and extension</td></tr><tr><th>Operating model</th><td><strong>Apache-licensed, self-managed</strong><br /><span>Controlled release posture</span></td><td>Commercial, packaged</td><td>Microsoft cloud ecosystem</td><td>Open, engineering-led</td></tr><tr><th>Catalog / quality / lineage breadth</th><td>Focused initial workflow<br /><span>PostgreSQL + Snowflake first</span></td><td><strong>Broad packaged portfolio</strong></td><td><strong>Broad Microsoft-native portfolio</strong></td><td><strong>Broad open metadata ecosystem</strong></td></tr><tr><th>Best-fit buyer question</th><td>“Can we prove the agent did not overstep?”</td><td>“How do we standardize enterprise governance?”</td><td>“How do we govern a Microsoft-centered estate?”</td><td>“How do we build an extensible metadata foundation?”</td></tr></tbody></table></div>
          <p className="market-disclosure"><ShieldCheck size={16} /><span><strong>Reading this comparison:</strong> the radar is a directional positioning profile based on public product documentation, not a third-party benchmark or procurement score. Validate every alternative against your required deployment, security, connector, support and compliance criteria.</span></p>
          <p className="market-sources">Public product references: <a href="https://www.collibra.com/products/collibra-platform" target="_blank" rel="noreferrer">Collibra</a> · <a href="https://www.alation.com/product/agentic-data-intelligence-platform/" target="_blank" rel="noreferrer">Alation</a> · <a href="https://atlan.com/active-data-governance/" target="_blank" rel="noreferrer">Atlan</a> · <a href="https://learn.microsoft.com/en-us/purview/data-governance-overview" target="_blank" rel="noreferrer">Microsoft Purview</a> · <a href="https://docs.datahub.com/docs/features" target="_blank" rel="noreferrer">DataHub</a> · <a href="https://open-metadata.org/" target="_blank" rel="noreferrer">OpenMetadata</a>.</p>
        </section>

        <section className="evidence-story">
          <div className="story-image"><AssetDossierVisual /><div className="image-caption"><Sparkles size={15} />From harvested fact to stewarded context</div></div>
          <div className="story-copy"><SectionMark>Evidence is the product</SectionMark><h2>Every asset should carry the context needed to use it responsibly.</h2><p>DataGenie keeps discovered metadata distinct from stewarded contributions, so a new harvest adds operational facts without erasing the human context that makes a dataset usable.</p><div className="story-stat-grid"><div><strong>Who</strong><span>Owner, steward and accountable domain</span></div><div><strong>What</strong><span>Technical schema, description and classification</span></div><div><strong>When</strong><span>Freshness, evidence timestamps and lifecycle</span></div><div><strong>Why</strong><span>Policy result, lineage impact and intended use</span></div></div></div>
        </section>

        <section id="governance" className="governance section-rail">
          <div className="governance-intro"><SectionMark>The governance model</SectionMark><h2>Agents can prepare intent. <em>Stewards govern change.</em></h2><p>DataGenie makes the separation explicit in the product, the API and the audit trail. A proposal is evidence for a decision; it is never the decision itself.</p></div>
          <div className="governance-layout">
            <div className="governance-workflow"><ProposalBoundaryVisual /><div className="workflow-overlay"><span className="workflow-label">Proposal-only boundary</span><strong>Recommendation ≠ governed change</strong><p>Every governed mutation stays behind a named steward review and server-enforced confirmation.</p></div></div>
            <div className="boundary-list">
              <div><span>01</span><p><strong>Agent or host creates structured intent.</strong> The request includes its source, evidence, change diff, policy snapshot and version preconditions.</p></div>
              <div><span>02</span><p><strong>The proposal is a pending inbox record.</strong> The asset remains unchanged while the steward sees impact, policy result and provenance.</p></div>
              <div><span>03</span><p><strong>Approval belongs to an authorized steward.</strong> The steward’s current role is checked at the protected service boundary, not inferred from the agent.</p></div>
              <div><span>04</span><p><strong>Execution requires a server-bound confirmation.</strong> The proposal hash, short-lived nonce, current policy and resource version are rechecked atomically before any mutation.</p></div>
            </div>
          </div>
          <div className="separation-proof"><LockKeyhole size={20} /><p><strong>Why route separation matters:</strong> the public/UI proposal path records reviewable intent, while the protected steward-inbox execution path receives the server-issued confirmation nonce and validates current authority. A model, browser client or MCP host cannot manufacture that confirmation context or reuse an old approval after policy, role or resource state changes.</p></div>
        </section>

        <section className="lineage-section"><div className="lineage-copy"><SectionMark>Lineage with operational meaning</SectionMark><h2>Understand what a change touches before the business feels it.</h2><p>DataGenie represents data relationships with typed provenance and confidence, then connects impact to the people who own the affected assets and reports.</p><div className="lineage-points"><EvidenceLine>Trace upstream sources and downstream consumers</EvidenceLine><EvidenceLine>Keep column-level relationships where evidence is available</EvidenceLine><EvidenceLine>Surface quality incidents in their operational context</EvidenceLine></div></div><div className="lineage-art"><LineageFlowVisual /><div className="lineage-tag"><Route size={15} />Bounded impact · confidence visible</div></div></section>

        <section id="docs" className="docs section-rail">
          <div className="docs-heading"><SectionMark>Documentation center</SectionMark><h2>What, why and how—without hiding the hard parts.</h2><p>Use these starting points to align product, platform, stewardship and support teams around a safe enterprise rollout.</p></div>
          <div className="docs-panel">
            <div className="docs-tabs" role="tablist" aria-label="Documentation topics">{(Object.keys(docs) as Array<keyof typeof docs>).map((key) => <button key={key} role="tab" aria-selected={docTab === key} className={docTab === key ? "is-active" : ""} onClick={() => setDocTab(key)}>{key === "what" ? "What it is" : key === "why" ? "Why it matters" : "How it works"}</button>)}</div>
            <div className="docs-content" role="tabpanel"><p className="docs-kicker">{activeDoc.kicker}</p><h3>{activeDoc.title}</h3><p>{activeDoc.body}</p><ul>{activeDoc.bullets.map((item) => <li key={item}><CheckCircle2 size={16} />{item}</li>)}</ul><div className="proof-strip"><span className="proof-chip proof-chip--system">● system context</span><span className="proof-chip proof-chip--healthy">● evidence current</span><span className="proof-chip proof-chip--review">◆ steward review</span></div></div>
            <aside className="docs-rail"><BookOpen size={20} /><strong>Core definitions</strong><a href="#catalog-definition">Catalog definition <ArrowRight size={14} /></a><a href="#governance">Steward proposal model <ArrowRight size={14} /></a><a href="#staging">Tenant staging guide <ArrowRight size={14} /></a><a href="#support">Request-ID support <ArrowRight size={14} /></a></aside>
          </div>
        </section>

        <section id="catalog-definition" className="definition-band"><div><SectionMark>Catalog definition</SectionMark><h2>A catalog is a governed record of an enterprise asset—not a second copy of the data.</h2></div><div className="definition-list"><p><strong>Discovered metadata</strong> is technical fact harvested from a source: identifiers, schema, column types, timestamps and ingestion state.</p><p><strong>Curated metadata</strong> is stewarded business context: description, tags, owner, classification, lifecycle and certification.</p><p><strong>Usable discovery</strong> occurs when a search leads to a trusted asset view, a certification request or an approved usage decision.</p></div></section>

        <section id="staging" className="staging section-rail"><div className="staging-intro"><SectionMark>Detailed staging walkthrough</SectionMark><h2>Prove tenant isolation and operational support before customer enablement.</h2><p>Run this sequence only in an approved non-production tenant with synthetic or explicitly approved test metadata. Do not use production tokens, source credentials, raw rows or a personal account.</p></div><div className="staging-grid"><div className="staging-steps">{[
          ["01", "Register the test boundary", "Record the approved test tenant, named host ID, business owner, security contact and support contact. Confirm the tenant is allowlisted for the beta."],
          ["02", "Configure the OAuth/OIDC client", "Use the DataGenie MCP protected-resource audience, approved HTTPS redirect/origin controls, a tenant claim, assigned DataGenie roles and a short-lived token policy."],
          ["03", "Start least privilege", "Begin with catalog:read. Add quality:read, lineage:read or governance:propose only when the named steward has accepted the corresponding workflow."],
          ["04", "Negotiate and discover", "Call initialize and tools/list. Verify the documented seven-tool surface and save the generated X-Request-ID in the host audit record."],
          ["05", "Exercise a governed read", "Call get_asset_context for a synthetic asset. Confirm provenance, policy, evidence, timestamp, confidence and redaction indicators remain structured."],
          ["06", "Prove scope denial", "With a separate token that lacks governance:propose, call a proposal tool. Expect a safe denial; do not retry with a broadened scope or tenant override."],
          ["07", "Walk the proposal boundary", "With governance:propose approved, create one test proposal. Confirm it appears as pending in the steward inbox, while the host cannot approve or execute it."],
          ["08", "Run the steward confirmation check", "A named authorized steward reviews the proposal. The protected service must recheck current role, policy, proposal hash, nonce expiry and resource version before execution."],
          ["09", "Perform the request-ID support dry run", "Search the ledger by the recorded request ID. Confirm tenant and host binding, operation, outcome, safe error code and duration; treat a missing ledger entry as fail-closed."],
        ].map(([number, title, body], index) => <div key={number} className={`staging-step ${flowOpen === index ? "is-open" : ""}`}><button onClick={() => setFlowOpen(flowOpen === index ? null : index)}><span>{number}</span><strong>{title}</strong><ChevronDown size={17} /></button>{flowOpen === index && <p>{body}</p>}</div>)}</div>
          <aside id="support" className="support-card"><div className="support-icon"><FileSearch size={23} /></div><p className="docs-kicker">Support dry run</p><h3>Use the request ID as the join key.</h3><p>Support should collect only the request ID, tenant, host ID, tool, UTC timestamp, protocol/helper version and safe error code.</p><code>host-2026-08-22-00017</code><div className="support-safe"><CheckCircle2 size={15} />Never request a bearer token, client secret, source credential, raw prompt, raw row or confirmation nonce.</div></aside></div></section>

        <section className="test-plan section-rail"><div className="test-plan-heading"><SectionMark>Detailed test plan</SectionMark><h2>Test the boundaries, not just the happy path.</h2><div className="test-proof-row"><span className="proof-chip proof-chip--system">● identity and scope</span><span className="proof-chip proof-chip--review">◆ pending is not applied</span><span className="proof-chip proof-chip--risk">▲ fail closed on mismatch</span></div></div><div className="test-table-wrap"><table><thead><tr><th>Test area</th><th>Scenario</th><th>Pass criteria</th><th>Evidence retained</th></tr></thead><tbody><tr><td>Tenant binding</td><td>Token tenant and host ID match approved test configuration.</td><td>Only tenant-scoped assets/ledger records are returned.</td><td>Request ID, safe tenant/host metadata.</td></tr><tr><td>OAuth audience</td><td>Valid and invalid protected-resource audience tokens.</td><td>Invalid audience receives safe 401; valid token reaches scope check.</td><td>Status, safe code, request ID.</td></tr><tr><td>Least privilege</td><td>Call proposal tool without governance:propose.</td><td>Safe deny; no proposal/inbox record created.</td><td>Request ID and ledger outcome.</td></tr><tr><td>Schema handling</td><td>Send malformed or extra tool arguments.</td><td>Structured validation error; no broadened interpretation.</td><td>Request ID, validation code.</td></tr><tr><td>Proposal separation</td><td>Create a permitted test proposal from an approved host.</td><td>Pending inbox record only; governed asset is unchanged.</td><td>Proposal ID, source/host, request ID.</td></tr><tr><td>Execution rechecks</td><td>Change role, policy, resource version, nonce or expiry after approval.</td><td>Execution blocks and preserves durable audit evidence.</td><td>Proposal status, safe reason, audit event.</td></tr><tr><td>Correlation</td><td>Investigate a known tool result by request ID.</td><td>Ledger matches tenant, host, tool, outcome and duration.</td><td>Sanitized support record.</td></tr></tbody></table></div></section>

        <section className="final-cta"><div className="cta-signal" aria-hidden="true"><span /><span /><span /><i /><i /></div><div><SectionMark>Build trust into the data estate</SectionMark><h2>Give every team a clearer route from data to decision.</h2></div><a href="https://github.com/itismohan/datagenie/tree/main/docs" target="_blank" rel="noreferrer" className="button button-light">Explore the documentation <ArrowRight size={17} /></a></section>
      </main>

      <footer><div className="footer-brand"><span className="footer-logo"><img src={LOGO_URL} alt="DataGenie" /></span><p>Discover · Trust · Govern · Empower</p></div><div className="footer-links"><a href="#platform">Platform</a><a href="#governance">Governance</a><a href="#docs">Documentation</a><a href="#staging">Staging guide</a></div><p className="footer-note">Governed data intelligence, grounded in evidence, lineage and accountable stewardship.</p></footer>
    </div>
  );
}
