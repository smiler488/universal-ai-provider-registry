#!/bin/sh
# Retrieve one complete, consistent release. Public metadata only; no API key.
set -eu
url=${1:-https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json}
curl --fail --location --connect-timeout 10 --max-time 60 "$url" --output catalog.json
python3 -c 'import json; c=json.load(open("catalog.json")); print(c["data_version"]); print("models:", len(c["models"])); print("deployments:", len(c["deployments"]))'
