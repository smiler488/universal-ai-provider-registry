// Read public metadata: node read_catalog.mjs [catalog-url] [provider-id].
// Requires Node.js 18+; no API key and no model invocation.
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
const providers = new Map(catalog.providers.map(p => [p.id, p]));
const providerId = process.argv[3];
if (providerId === undefined) {
  console.log("Sample provider IDs (the full list is in providers.json):");
  for (const provider of catalog.providers.slice(0, 10)) {
    console.log(provider.id, "—", provider.name);
  }
  console.log("Pass an exact provider ID as the second argument to inspect its deployments.");
} else {
  if (!providers.has(providerId)) {
    throw new Error("Unknown provider ID; choose an exact id from providers.json");
  }
  const models = new Map(catalog.models.map(m => [m.id, m]));
  const developers = new Map(catalog.developers.map(d => [d.id, d]));
  const deployments = catalog.deployments.filter(d => d.provider_id === providerId);
  console.log(`${providerId}: ${deployments.length} deployments; showing at most 10`);
  for (const deployment of deployments.slice(0, 10)) {
    const model = models.get(deployment.model_id);
    const developer = developers.get(model.developer_id);
    console.log(JSON.stringify({
      provider_model_id: deployment.provider_model_id,
      model_id: model.id,
      model_name: model.name,
      developer: developer?.name ?? null,
      availability: deployment.availability,
      pricing_status: deployment.pricing_status,
      conflicts: deployment.conflicts,
    }));
  }
}
