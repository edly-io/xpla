# LTI 1.3 Tool Provider

xPLA LTI 1.3 tool provider for integrating xPLA activities into Learning Management Systems (Canvas, Moodle, Open edX, etc.) via the IMS Global LTI 1.3 standard.

## Features

- **LTI 1.3 Security Framework:** Full OIDC authentication, JWT validation, nonce replay protection
- **Deep Linking:** Instructors can select xPLA activities from the tool to add to their courses
- **Resource Link Launches:** Students launch activities with their identity and context
- **Admin UI:** Web interface for managing registered LMS platforms
- **Multi-tenant:** Support multiple LMS platforms with isolated configurations

## Running

From the project root:

```bash
make lti-server  # Start on port 9754
```

Then open http://127.0.0.1:9754/admin/platforms to manage platforms.

## Configuration

### Environment Variables

- `LTI_BASE_URL` - Public base URL of the tool (default: `http://127.0.0.1:9754`)

### Registering an LMS Platform

1. Navigate to http://127.0.0.1:9754/admin/platforms
2. Click "Add Platform"
3. Enter platform configuration:
   - **Name:** Display name (e.g., "Canvas Production")
   - **Issuer:** Platform's issuer URL (e.g., `https://canvas.instructure.com`)
   - **Client ID:** Obtained from LMS registration
   - **OIDC Auth URL:** Platform's OIDC authentication endpoint
   - **JWKS URL:** Platform's public keyset URL
   - **Access Token URL:** (Optional) Platform's OAuth2 token endpoint

### Configuring in Your LMS

Provide these URLs to your LMS during tool registration:

- **OpenID Connect Login URL:** `{BASE_URL}/auth/login`
- **Launch URL / Redirect URI:** `{BASE_URL}/auth/callback`
- **Public Keyset URL:** `{BASE_URL}/.well-known/jwks.json`

Replace `{BASE_URL}` with your `LTI_BASE_URL` (e.g., `http://127.0.0.1:9754` for local dev).

### Example: Open edX

1. In Open edX Studio, configure LTI 1.3 tool with:
   - Tool Launch URL: `http://127.0.0.1:9754/auth/login`
   - Redirect URI: `http://127.0.0.1:9754/auth/callback`
   - Public Keyset URL: `http://127.0.0.1:9754/.well-known/jwks.json`

2. Copy the issuer, client_id, and URLs from Open edX

3. Register the platform in xPLA admin UI at http://127.0.0.1:9754/admin/platforms

## Architecture

```
┌─────────────────────┐           ┌──────────────────────┐
│  LMS (Canvas,       │  LTI 1.3  │  xPLA LTI Provider   │
│  Moodle, Open edX)  │ ────────► │  (port 9754)         │
│                     │           │                      │
│  - OIDC login       │           │  - Admin UI          │
│  - JWT signing      │           │  - OIDC handler      │
│  - Deep linking     │           │  - JWT validation    │
└─────────────────────┘           │  - Activity launcher │
                                  └──────────────────────┘
```

### Core Components

**Backend** ([app.py](./app.py)): FastAPI server handling OIDC login, launch callbacks, admin CRUD, and activity rendering.

**Database** ([core/db.py](./core/db.py)): SQLite database at `dist/lti/lti.db` storing:
- **Platform:** Registered LMS instances (issuer, client_id, OIDC URLs)
- **Deployment:** LTI deployment IDs per platform
- **Nonce:** One-time nonce values for replay protection (10-minute TTL)

**Security** ([core/keys.py](./core/keys.py)): RSA key pair at `dist/lti/private.pem` for:
- Signing Deep Linking response JWTs
- Publishing JWKS endpoint for signature verification

**Integration** ([integration.py](./integration.py)): Maps LTI launch data to xPLA `ActivityContext`:
- Extracts activity type from custom parameters
- Creates session tokens for activity access
- Handles Deep Linking activity selection

## API Endpoints

**Authentication:**
- `GET/POST /auth/login` - OIDC login initiation (LMS calls this)
- `POST /auth/callback` - LTI launch callback (receives JWT from LMS)
- `GET /.well-known/jwks.json` - Public keyset for JWT signature verification

**Admin UI:**
- `GET /admin/platforms` - List registered platforms
- `GET /admin/platforms/new` - New platform form
- `POST /admin/platforms` - Create platform
- `GET /admin/platforms/{id}/edit` - Edit platform form
- `POST /admin/platforms/{id}` - Update platform
- `POST /admin/platforms/{id}/delete` - Delete platform

**Activity Rendering:**
- `GET /activity/{token}` - Render activity page (token-gated)
- `GET /activity/{token}/assets/{path}` - Serve activity assets
- `POST /activity/{token}/actions/{action}` - Submit activity action
- `WS /activity/{token}/ws` - WebSocket for real-time events

**Deep Linking:**
- `POST /deep-link/respond` - Generate and submit Deep Linking response JWT

## Data Model

Defined in [core/models.py](./core/models.py):

- **Platform** - Registered LMS instance with OIDC configuration
- **Deployment** - LTI deployment ID linking to a platform
- **Nonce** - One-time nonce for replay protection with expiration

## Development

### Running Tests

```bash
# All LTI tests
pytest src/tests/lti/ -v

# Specific test modules
pytest src/tests/lti/test_models.py -v      # Database models
pytest src/tests/lti/test_keys.py -v        # RSA keys & JWKS
pytest src/tests/lti/test_oidc.py -v        # OIDC login flow
pytest src/tests/lti/test_launch.py -v      # JWT validation
pytest src/tests/lti/test_admin_api.py -v   # Admin CRUD API
```

### Database

SQLite database at `dist/lti/lti.db`. To inspect:

```bash
sqlite3 dist/lti/lti.db
.tables
select * from platform;
```

### Key Management

RSA key pair stored at `dist/lti/private.pem`. Generated automatically on first run.

To view public JWKS:
```bash
curl http://127.0.0.1:9754/.well-known/jwks.json | jq
```

## LTI 1.3 Flow

### Resource Link Launch

1. **LMS initiates:** Calls `/auth/login` with `iss`, `client_id`, `login_hint`
2. **Tool validates:** Looks up platform, generates state + nonce
3. **Tool redirects:** Sends user to LMS OIDC auth URL
4. **LMS authenticates:** User authenticates with LMS
5. **LMS sends JWT:** POST to `/auth/callback` with signed `id_token`
6. **Tool validates:** Verifies JWT signature, checks nonce, extracts claims
7. **Tool launches:** Creates session token, renders activity

### Deep Linking

1. **Instructor initiates:** Launches deep linking request from LMS
2. **Tool receives:** JWT with `LtiDeepLinkingRequest` message type
3. **Tool displays:** Activity selection UI
4. **Instructor selects:** Chooses activity to add to course
5. **Tool responds:** Creates JWT with selected activity, submits to LMS
6. **LMS creates link:** Adds resource link to course

## Security

- **OIDC Authentication:** Standard OAuth2/OIDC flow with state parameter
- **JWT Validation:** Verifies signature using platform's public key from JWKS
- **Nonce Replay Protection:** One-time nonce values expire after 10 minutes
- **Session Tokens:** Signed JWT tokens for activity access control
- **HTTPS Required:** Production deployments should use HTTPS for security

## Troubleshooting

### "Unknown platform" error

- Verify platform is registered in admin UI
- Check issuer and client_id match exactly
- Ensure platform sends correct `iss` and `client_id` in login request

### JWT validation fails

- Verify platform's JWKS URL is correct and accessible
- Check platform's clock is synchronized (JWT expiration)
- Inspect JWT claims: `jwt.io` or `python -c "import jwt; print(jwt.decode(..., options={'verify_signature': False}))"`

### Deep linking doesn't work

- Verify LMS supports LTI 1.3 Deep Linking
- Check deep_link_return_url in launch JWT
- Inspect tool's Deep Linking response JWT signature

## Standards Compliance

- **LTI 1.3 Core Specification:** [IMS Global LTI 1.3](https://www.imsglobal.org/spec/lti/v1p3/)
- **LTI Deep Linking 2.0:** [Deep Linking Spec](https://www.imsglobal.org/spec/lti-dl/v2p0)
- **Security Framework:** [LTI Security](https://www.imsglobal.org/spec/security/v1p0/)
