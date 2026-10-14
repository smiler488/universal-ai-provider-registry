"""Read public registry metadata; requires Python 3.11+, no API key."""

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

    # Text matching is for exploration only, never canonical identity merging.
    matches = [m for m in catalog["models"] if "mimo" in json.dumps(m).lower()]
    print("MiMo-related model records:")
    for model in matches:
        print(model["id"])


if __name__ == "__main__":
    main()
