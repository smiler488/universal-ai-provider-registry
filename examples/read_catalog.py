"""Read public metadata: python read_catalog.py [catalog-url] [provider-id]."""

import json
import sys
from urllib.request import urlopen

URL = "https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json"


def main():
    # An optional URL is useful when testing a local HTTP preview.
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    with urlopen(url, timeout=30) as response:
        catalog = json.load(response)
    if catalog["schema_version"] != "1.0.0":
        raise ValueError("Review this client's compatibility with the schema version")
    print("Data version:", catalog["data_version"])
    print("Generated at:", catalog["generated_at"])
    for key in ("models", "developers", "providers", "deployments", "sources"):
        print(f"{key}: {len(catalog[key])}")

    providers = {p["id"]: p for p in catalog["providers"]}
    if len(sys.argv) < 3:
        print("Sample provider IDs (the full list is in providers.json):")
        for provider in catalog["providers"][:10]:
            print(provider["id"], "—", provider["name"])
        print("Pass an exact provider ID as the second argument to inspect its deployments.")
        return

    provider_id = sys.argv[2]
    if provider_id not in providers:
        raise ValueError("Unknown provider ID; choose an exact id from providers.json")
    models = {m["id"]: m for m in catalog["models"]}
    developers = {d["id"]: d for d in catalog["developers"]}
    deployments = [d for d in catalog["deployments"] if d["provider_id"] == provider_id]
    print(f"{provider_id}: {len(deployments)} deployments; showing at most 10")
    for deployment in deployments[:10]:
        model = models[deployment["model_id"]]
        developer = developers.get(model["developer_id"])
        print(json.dumps({
            "provider_model_id": deployment["provider_model_id"],
            "model_id": model["id"],
            "model_name": model["name"],
            "developer": developer["name"] if developer else None,
            "availability": deployment["availability"],
            "pricing_status": deployment["pricing_status"],
            "conflicts": deployment["conflicts"],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
