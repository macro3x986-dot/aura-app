#!/usr/bin/env python3
"""AURA — MAVIXOR Signature Verifier
Usage: python verify_aura.py <protected_file.py>
"""
import sys
import re
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

AURA_MARKER = "# === END AURA METADATA (DO NOT REMOVE) ===\n"


def verify(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"[!] Cannot read file: {e}")
        return False

    if AURA_MARKER not in content:
        print("[!] Not an AURA-protected file (marker missing).")
        return False

    header, code = content.split(AURA_MARKER, 1)

    m_hash = re.search(r"# SHA256:\s*([a-f0-9]+)", header)
    m_sig = re.search(r"# ED25519-SIGNATURE:\s*([A-Za-z0-9+/=]+)", header)
    m_pub = re.search(r"# ED25519-PUBKEY:\s*([A-Za-z0-9+/=]+)", header)

    if not (m_hash and m_sig and m_pub):
        print("[!] Malformed AURA metadata block.")
        return False

    expected_hash = m_hash.group(1)
    signature = base64.b64decode(m_sig.group(1))
    pub_raw = base64.b64decode(m_pub.group(1))
    pub = Ed25519PublicKey.from_public_bytes(pub_raw)

    actual_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

    if actual_hash != expected_hash:
        print("[!] HASH MISMATCH — file was modified.")
        print(f"    expected: {expected_hash}")
        print(f"    actual:   {actual_hash}")
        return False

    try:
        pub.verify(signature, code.encode("utf-8"))
    except Exception:
        print("[!] SIGNATURE INVALID — file was tampered with.")
        return False

    print("[+] SHA-256 OK")
    print("[+] ED25519 SIGNATURE OK")
    print("[+] AURA — MAVIXOR SIGNATURE PROTECTOR")
    print("    File is authentic and unmodified.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_aura.py <protected_file.py>")
        sys.exit(1)
    sys.exit(0 if verify(sys.argv[1]) else 1)