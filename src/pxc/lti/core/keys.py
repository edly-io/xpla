"""RSA key management for LTI 1.3 tool provider."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jwcrypto import jwk
import jwt


@dataclass
class KeySet:
    """Holds the tool's RSA key pair and provides signing/JWKS helpers."""

    private_key: jwk.JWK

    @property
    def kid(self) -> str:
        """Return key ID, using thumbprint if not explicitly set."""
        kid: str | None = self.private_key.key_id
        if kid is None:
            kid = self.private_key.thumbprint()
        return kid

    @property
    def private_pem(self) -> str:
        pem: str = self.private_key.export_to_pem(
            private_key=True, password=None
        ).decode()
        return pem

    @property
    def public_pem(self) -> str:
        pem: str = self.private_key.export_to_pem(
            private_key=False, password=None
        ).decode()
        return pem

    def sign_jwt(self, payload: dict[str, Any]) -> str:
        """Sign a JWT with the tool's private key."""
        token: str = jwt.encode(
            payload, self.private_pem, algorithm="RS256", headers={"kid": self.kid}
        )
        return token

    def jwks(self) -> dict[str, Any]:
        """Return JWKS dict containing the public key."""
        pub = self.private_key.export_public()
        pub_dict: dict[str, Any] = jwk.JWK(**json.loads(pub)).export(as_dict=True)
        pub_dict["use"] = "sig"
        pub_dict["alg"] = "RS256"
        pub_dict["kid"] = self.kid
        return {"keys": [pub_dict]}


def load_or_create_key(key_path: Path) -> KeySet:
    """Load an existing RSA key or generate a new one."""
    if key_path.exists():
        pem_data = key_path.read_text()
        key = jwk.JWK.from_pem(pem_data.encode())
    else:
        key = jwk.JWK.generate(kty="RSA", size=2048)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        pem: str = key.export_to_pem(private_key=True, password=None).decode()
        key_path.write_text(pem)
    return KeySet(private_key=key)
