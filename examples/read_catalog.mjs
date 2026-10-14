// Read public registry metadata with Node.js 18+; no API key.
const url = process.argv[2]
  ?? "https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json";
const response = await fetch(url, { signal: AbortSignal.timeout(30_000) });
if (!response.ok) throw new Error(`Registry HTTP ${response.status}`);
const catalog = await response.json();
if (catalog.schema_version !== "1.0.0") {
  throw new Error("Review this client's compatibility with the schema version");
}
console.log("Data version:", catalog.data_version);
console.log("Generated at:", catalog.generated_at);
for (const key of ["models", "developers", "providers", "deployments", "sources"]) {
  console.log(`${key}: ${catalog[key].length}`);
}
// Text matching is for exploration only, never canonical identity merging.
const matches = catalog.models.filter(m => JSON.stringify(m).toLowerCase().includes("mimo"));
console.log("MiMo-related model records:");
for (const model of matches) console.log(model.id);
