#!/usr/bin/env python3
"""
API Key Generator for NetOps MCP.

This script generates secure API keys for authentication.
The plain key is printed ONCE to stdout; config files receive only
'sha256:<hex>' digests (the format required by SecurityConfig).
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netops_mcp.middleware.auth import generate_api_key, hash_api_key


def main() -> None:
    """Generate API keys."""
    parser = argparse.ArgumentParser(
        description="Generate API keys for NetOps MCP authentication"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of API keys to generate (default: 1)"
    )
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=32,
        help="Length of API key (default: 32)"
    )
    parser.add_argument(
        "--hash",
        action="store_true",
        help="Also output hashed versions of keys"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Add keys to config file (path to config.json)"
    )
    
    args = parser.parse_args()
    
    # Generate keys (digest always computed — it is what goes into config)
    keys = []
    for _ in range(args.count):
        key = generate_api_key(args.length)
        key_data = {
            "key": key,
            "hash": f"sha256:{hash_api_key(key)}",
        }
        keys.append(key_data)
    
    # Output keys
    if args.json:
        print(json.dumps(keys, indent=2))
    else:
        print("=" * 80)
        print("NetOps MCP API Keys")
        print("=" * 80)
        print()
        
        for i, key_data in enumerate(keys, 1):
            print(f"Key #{i}:")
            print(f"  API Key: {key_data['key']}")
            if args.hash:
                print(f"  Hash:    {key_data['hash']}")
            print()

        print("=" * 80)
        print("IMPORTANT: Save the plain API key(s) NOW - they are not stored anywhere.")
        print("This is your only chance to copy them; only 'sha256:<hex>' digests")
        print("belong in config.json under security.api_keys.")
        print("=" * 80)
    
    # Optionally add to config file
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"\nError: Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Ensure security section exists
            if 'security' not in config:
                config['security'] = {}
            
            # Ensure api_keys array exists
            if 'api_keys' not in config['security']:
                config['security']['api_keys'] = []
            
            # Add new keys as sha256:<hex> digests — plain keys never touch disk
            for key_data in keys:
                config['security']['api_keys'].append(key_data['hash'])

            # Enable authentication
            config['security']['require_auth'] = True

            # Write back to file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"\n✓ Added {len(keys)} hashed key(s) to {config_path}")
            print("✓ Authentication enabled (require_auth: true)")
            print("✓ Only sha256 digests were written; the plain key(s) above are NOT stored")
            
        except Exception as e:
            print(f"\nError updating config file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()


