"""Select available SDK images without changing upstream architecture rows."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


REPOSITORY = "lochnair/openwrt-sdk-rust"
ACCEPT = ", ".join(("application/vnd.oci.image.index.v1+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.docker.distribution.manifest.v2+json"))


def rust_image_exists(tag):
    """Only a structured registry not-found response permits fallback."""
    query = urllib.parse.urlencode({"service": "registry.docker.io",
                                    "scope": f"repository:{REPOSITORY}:pull"})
    with urllib.request.urlopen(f"https://auth.docker.io/token?{query}", timeout=60) as response:
        token = json.load(response)["token"]
    request = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{REPOSITORY}/manifests/{tag}",
        headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT})
    try:
        with urllib.request.urlopen(request, timeout=60):
            return True
    except urllib.error.HTTPError as error:
        with error:
            if error.code == 404:
                try:
                    errors = json.load(error)["errors"]
                    if errors and all(item["code"] in ("MANIFEST_UNKNOWN", "NAME_UNKNOWN")
                                      for item in errors):
                        return False
                except (ValueError, KeyError, TypeError):
                    pass
        raise


def sdk_matrix(matrix):
    rows = matrix["include"]
    if not rows:
        raise ValueError("Empty OpenWrt matrix")
    seen = set()
    result = []
    for row in rows:
        key = (row["version"], row["package_arch"])
        if key in seen:
            raise ValueError(f"Duplicate version/architecture: {key}")
        seen.add(key)
        tag = f"{row['target'].replace('/', '-')}-{row['version']}"
        rust = rust_image_exists(tag)
        image = f"{REPOSITORY}:{tag}" if rust else f"ghcr.io/openwrt/sdk:{tag}"
        result.append({**row, "image": image, "rust": rust})
    return {"include": result}


def main():
    matrix = sdk_matrix(json.loads(os.environ["OPENWRT_MATRIX"]))
    encoded = json.dumps(matrix, separators=(",", ":"))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"matrix={encoded}\n")
    print(encoded)


if __name__ == "__main__":
    main()
