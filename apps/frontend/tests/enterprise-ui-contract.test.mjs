import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const app = readFileSync(resolve(root, "src/pages/App.jsx"), "utf8");
const styles = readFileSync(resolve(root, "src/styles.css"), "utf8");
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));

for (const workspace of ["Control center", "Catalog intelligence", "Quality evidence", "Lineage intelligence", "Proposal inbox", "Administration posture"]) {
  assert.ok(app.includes(workspace), `Expected ${workspace} workspace content.`);
}
for (const requiredGovernanceSignal of ["Proposal-only boundary", "Human review required", "Confirmation remains server-bound", "View evidence and review route"]) {
  assert.ok(app.includes(requiredGovernanceSignal), `Expected safe governance signal: ${requiredGovernanceSignal}`);
}
for (const forbiddenControl of [">Approve<", ">Execute<", "confirmation nonce input", "execute_proposal"]) {
  assert.ok(!app.includes(forbiddenControl), `Direct governance control must not be present: ${forbiddenControl}`);
}
for (const supportSignal of ["X-Request-ID", "Request ID", "Do not share tokens", "synthetic demonstration assets"]) {
  assert.ok(app.includes(supportSignal), `Expected safe support/data-handling signal: ${supportSignal}`);
}
for (const responsiveSignal of ["@media (max-width: 980px)", "@media (max-width: 720px)", ":focus-visible", ".sidebar--open"]) {
  assert.ok(styles.includes(responsiveSignal), `Expected responsive/accessibility style: ${responsiveSignal}`);
}
assert.ok(app.includes('src="/datagenie.png"'), "Expected the approved DataGenie logo in the product shell.");
assert.equal(packageJson.scripts.build, "vite build");

console.log("Enterprise UI contract checks passed.");
