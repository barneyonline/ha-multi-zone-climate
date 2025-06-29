#!/usr/bin/env python3
import sys
import yaml

def validate(path):
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"YAML error in {path}: {exc}", file=sys.stderr)
            return False
    if not isinstance(data, dict):
        print(f"{path} must contain a YAML mapping", file=sys.stderr)
        return False
    if 'blueprint' not in data:
        print(f"{path} missing 'blueprint' section", file=sys.stderr)
        return False
    bp = data['blueprint']
    if not isinstance(bp, dict):
        print("'blueprint' section must be a mapping", file=sys.stderr)
        return False
    for key in ('name', 'domain'):
        if key not in bp:
            print(f"'blueprint' missing required key '{key}'", file=sys.stderr)
            return False
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_blueprint.py <blueprint.yaml>", file=sys.stderr)
        sys.exit(1)
    if validate(sys.argv[1]):
        print("Blueprint format valid")
    else:
        sys.exit(1)
