"""Add SDK image names without changing the upstream architecture selection."""

import json
import os


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
        image = f"lochnair/openwrt-sdk-rust:{row['target'].replace('/', '-')}-{row['version']}"
        result.append({**row, "image": image})
    return {"include": result}


if __name__ == "__main__":
    matrix = sdk_matrix(json.loads(os.environ["OPENWRT_MATRIX"]))
    encoded = json.dumps(matrix, separators=(",", ":"))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"matrix={encoded}\n")
    print(encoded)
