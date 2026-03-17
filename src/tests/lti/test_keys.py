"""Tests for RSA key management."""

from pathlib import Path

import jwt

from xpla.lti.core.keys import KeySet, load_or_create_key


class TestLoadOrCreateKey:
    """Tests for load_or_create_key function."""

    def test_creates_new_key_when_file_missing(self, tmp_path: Path) -> None:
        """Should create a new RSA key when file doesn't exist."""
        key_path = tmp_path / "new_key.pem"
        assert not key_path.exists()

        key_set = load_or_create_key(key_path)

        assert key_path.exists()
        assert isinstance(key_set, KeySet)
        assert key_set.private_key is not None

    def test_loads_existing_key(self, tmp_path: Path) -> None:
        """Should load an existing key from PEM file."""
        key_path = tmp_path / "existing_key.pem"

        # Create a key first
        key_set1 = load_or_create_key(key_path)
        kid1 = key_set1.kid

        # Load the same key
        key_set2 = load_or_create_key(key_path)
        kid2 = key_set2.kid

        assert kid1 == kid2

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        key_path = tmp_path / "subdir" / "another" / "key.pem"
        assert not key_path.parent.exists()

        _ = load_or_create_key(key_path)

        assert key_path.exists()
        assert key_path.parent.exists()


class TestKeySet:
    """Tests for KeySet class."""

    def test_kid_property(self, test_key_set: KeySet) -> None:
        """Should return a non-empty key ID."""
        assert test_key_set.kid
        assert isinstance(test_key_set.kid, str)

    def test_private_pem_property(self, test_key_set: KeySet) -> None:
        """Should export private key as PEM."""
        pem = test_key_set.private_pem
        assert "-----BEGIN PRIVATE KEY-----" in pem
        assert "-----END PRIVATE KEY-----" in pem

    def test_public_pem_property(self, test_key_set: KeySet) -> None:
        """Should export public key as PEM."""
        pem = test_key_set.public_pem
        assert "-----BEGIN PUBLIC KEY-----" in pem
        assert "-----END PUBLIC KEY-----" in pem

    def test_sign_jwt_produces_valid_token(self, test_key_set: KeySet) -> None:
        """Should sign a JWT with RS256."""
        payload = {"sub": "user123", "name": "Test User"}
        token = test_key_set.sign_jwt(payload)

        # Decode without verification to check structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["sub"] == "user123"
        assert decoded["name"] == "Test User"

        # Check header contains kid
        header = jwt.get_unverified_header(token)
        assert header["kid"] == test_key_set.kid
        assert header["alg"] == "RS256"

    def test_sign_jwt_can_be_verified(self, test_key_set: KeySet) -> None:
        """Should produce a JWT that can be verified with the public key."""
        payload = {"sub": "user123", "aud": "test-audience"}
        token = test_key_set.sign_jwt(payload)

        # Verify with public key
        decoded = jwt.decode(
            token,
            test_key_set.public_pem,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        assert decoded["sub"] == "user123"

    def test_jwks_returns_valid_structure(self, test_key_set: KeySet) -> None:
        """Should return a valid JWKS structure."""
        jwks = test_key_set.jwks()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1

        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == test_key_set.kid
        assert "n" in key  # RSA modulus
        assert "e" in key  # RSA exponent

    def test_jwks_contains_public_key_only(self, test_key_set: KeySet) -> None:
        """Should not expose private key components in JWKS."""
        jwks = test_key_set.jwks()
        key = jwks["keys"][0]

        # Public key should have n and e
        assert "n" in key
        assert "e" in key

        # Private key components should not be present
        assert "d" not in key
        assert "p" not in key
        assert "q" not in key

    def test_kid_consistent_across_operations(self, test_key_set: KeySet) -> None:
        """Key ID should be consistent across all operations."""
        kid1 = test_key_set.kid
        jwt_token = test_key_set.sign_jwt({"test": "data"})
        header = jwt.get_unverified_header(jwt_token)
        kid2 = header["kid"]
        jwks = test_key_set.jwks()
        kid3 = jwks["keys"][0]["kid"]

        assert kid1 == kid2 == kid3
