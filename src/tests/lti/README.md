# LTI 1.3 Tests

Comprehensive test suite for the PXC LTI 1.3 tool provider implementation.

## Running Tests

### All LTI tests:
```bash
source .venv/bin/activate
pytest src/tests/lti/ -v
```

### Specific test modules:
```bash
pytest src/tests/lti/test_models.py -v      # Database models (7 tests)
pytest src/tests/lti/test_keys.py -v        # RSA key management (11 tests)
pytest src/tests/lti/test_oidc.py -v        # OIDC login flow (11 tests)
pytest src/tests/lti/test_deep_linking.py -v # Deep linking (7 tests)
pytest src/tests/lti/test_launch.py -v      # JWT validation (19 tests)
pytest src/tests/lti/test_admin_api.py -v   # Admin CRUD (10 tests)
pytest src/tests/lti/test_integration.py -v # End-to-end (16 tests)
```

### With coverage:
```bash
pytest src/tests/lti/ --cov=src/pxc/lti --cov-report=html
open htmlcov/index.html
```

## Test Status

**Total Tests:** 81
**Passing:** 45 (55.6%)

### ✅ Fully Passing Modules
- `test_models.py` - 7/7 tests passing
- `test_keys.py` - 11/11 tests passing
- `test_oidc.py` - 11/11 tests passing
- `test_deep_linking.py` - 7/7 tests passing

### ⚠️  Needs Work
- `test_launch.py` - 7/19 passing (JWKS mocking issue)
- `test_admin_api.py` - 0/10 passing (database fixture issue)
- `test_integration.py` - 9/16 passing (JWKS + template issues)

See [lti-testing-status.md](../../../docs/lti-testing-status.md) for detailed status and fixes needed.

## Test Structure

```
src/tests/lti/
├── conftest.py              # Shared pytest fixtures
├── test_models.py           # SQLModel database schema tests
├── test_keys.py             # RSA key generation & JWKS tests
├── test_oidc.py             # OIDC login & nonce management tests
├── test_launch.py           # JWT validation & claim extraction tests
├── test_deep_linking.py     # Deep linking response JWT tests
├── test_admin_api.py        # Admin CRUD endpoint tests
└── test_integration.py      # End-to-end integration tests
```

## Key Fixtures (conftest.py)

- `db_engine` - In-memory SQLite database
- `db_session` - Database session
- `test_platform` - Sample LMS platform
- `test_deployment` - Sample deployment
- `test_key_set` - Tool's RSA keypair
- `platform_key_set` - Platform's RSA keypair (for signing test JWTs)
- `mock_platform_jwks` - Mocked JWKS endpoint
- `valid_id_token` - Pre-signed valid LTI launch JWT
- `deep_linking_id_token` - Pre-signed deep linking JWT

## Dependencies

- `pytest` - Test framework
- `responses` - HTTP mocking library

Install with:
```bash
pip install responses
```

## Notes

- Tests use in-memory SQLite databases
- Timezone handling fixed for SQLite datetime comparisons
- Key ID generation uses thumbprint when not explicitly set
