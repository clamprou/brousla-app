# Brousla - AI Content Creation App with Cloud Subscription

A complete cloud subscription layer integrated with Electron, supporting local dev mode and cloud-based licensing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Brousla App (Electron)                   │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │   Login UI   │───▶│  Auth Utils  │───▶│  License Utils  │  │
│  └──────────────┘    └──────────────┘    └─────────────────┘  │
│         │                    │                     │            │
│         │                    │                     │            │
│         └────────────────────┼─────────────────────┘            │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               │ HTTPS/REST
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Brousla Cloud (FastAPI)                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │ Auth Routes  │  │ Entitlements │  │  Stripe Webhooks  │    │
│  │              │  │   + License  │  │                   │    │
│  │ /register    │  │    JWT       │  │  /stripe/webhook  │    │
│  │ /login       │  │              │  │                   │    │
│  └──────────────┘  └──────────────┘  └───────────────────┘    │
│         │                  │                    │               │
│         └──────────────────┼────────────────────┘               │
│                            │                                    │
│                            ▼                                    │
│                    ┌──────────────┐                             │
│                    │  PostgreSQL  │                             │
│                    │              │                             │
│                    │ - users      │                             │
│                    │ - devices    │                             │
│                    │ - subs       │                             │
│                    │ - plans      │                             │
│                    │ - usage      │                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ Webhooks
                               ▼
                       ┌──────────────┐
                       │    Stripe    │
                       └──────────────┘
```

## Authentication & Licensing Flow

### 1. Initial Login Flow

```
User                App                 Cloud API           Stripe
  │                  │                      │                 │
  │──Login Form───▶  │                      │                 │
  │                  │──POST /auth/login──▶ │                 │
  │                  │                      │                 │
  │                  │◀─access_jwt──────────│                 │
  │                  │                      │                 │
  │                  │──POST /devices/──────▶│                 │
  │                  │    register          │                 │
  │                  │                      │                 │
  │                  │──GET /entitlements──▶│                 │
  │                  │                      │                 │
  │                  │◀─license_jwt─────────│                 │
  │                  │  (RS256 signed)      │                 │
  │                  │                      │                 │
  │◀─App Ready────   │                      │                 │
  │                  │                      │                 │
```

### 2. Subscription Upgrade Flow

```
User              App            Cloud API        Stripe
  │                │                 │               │
  │──Upgrade─────▶ │                 │               │
  │                │                 │               │
  │                │──POST /billing/─▶│               │
  │                │  create-checkout│               │
  │                │                 │               │
  │                │◀─checkout_url───│               │
  │                │                 │               │
  │◀─Open Browser─ │                 │               │
  │                │                 │               │
  │──────────────────────────────────┼──Checkout────▶│
  │                │                 │               │
  │                │                 │◀──Webhook─────│
  │                │                 │  (sub.created)│
  │                │                 │               │
  │                │──GET /entitle───▶│               │
  │                │   (polling)     │               │
  │                │                 │               │
  │                │◀─PRO license────│               │
  │                │                 │               │
```

### 3. Offline Grace Period

```
Online Mode              Offline Mode (Grace: 72h)
     │                           │
     │──Cached license_jwt──────▶│
     │   + timestamp             │
     │                           │
     │                      Verify:
     │                      - exp is past ✗
     │                      - But cached < 72h ✓
     │                           │
     │                      Allow access
     │                      (degraded)
     │                           │
```

## Setup Instructions

### 1. Setup Brousla Cloud Service

```bash
cd brousla-cloud

# Generate RSA key pair for JWT signing
python3 scripts/generate_keys.py

# Copy output to .env file
cp .env.example .env
# Edit .env and paste the generated keys

# Add your Stripe keys
# Get from: https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET=sk_test_...
STRIPE_WH_SECRET=whsec_...  # From webhook setup

# Start services
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

### 2. Setup Stripe Webhook

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Forward webhooks to local
stripe listen --forward-to localhost:8000/stripe/webhook

# Or in production, add webhook endpoint:
# https://dashboard.stripe.com/webhooks
# Endpoint: https://your-domain.com/stripe/webhook
# Events: customer.subscription.*, checkout.session.completed
```

### 3. Create Stripe Products

```bash
# Create PRO product
stripe products create --name="Brousla PRO"
stripe prices create --product=<PRODUCT_ID> \
  --unit-amount=1900 \
  --currency=usd \
  --recurring[interval]=month

# Copy price_id to .env as STRIPE_PRICE_ID_PRO

# Create TEAM product
stripe products create --name="Brousla TEAM"
stripe prices create --product=<PRODUCT_ID> \
  --unit-amount=4900 \
  --currency=usd \
  --recurring[interval]=month

# Copy price_id to .env as STRIPE_PRICE_ID_TEAM
```

### 4. Setup Electron App

```bash
cd ../  # Back to app root

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Edit .env
BROUSLA_CLOUD_URL=http://localhost:8000

# Start development
npm run electron-dev
```

## Testing

### Test Cloud Service

```bash
cd brousla-cloud

# Run unit tests
pytest

# Test auth endpoint
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","pwd":"password123"}'

# Response: {"access_token":"...", "token_type":"bearer"}
```

### Test Stripe Integration (Test Mode)

Use Stripe test cards:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`

```bash
# Test webhook locally
stripe trigger customer.subscription.created
```

### Test Electron App

1. **Local Dev Mode**
   - Start app
   - Click "Use Local Dev Mode"
   - Enter any email
   - No cloud connection needed

2. **Cloud Mode**
   - Start app
   - Register new account
   - Check console for license JWT
   - Try upgrading to PRO plan
   - Use test card: 4242 4242 4242 4242

3. **Offline Mode**
   - Login and get license
   - Stop cloud service
   - Restart app
   - Should work within 72h grace period

## Environment Variables

### Cloud Service (`.env`)

```bash
DATABASE_URL=postgresql://user:pass@db:5432/brousla_cloud
JWT_PRIVATE_KEY_PEM="-----BEGIN RSA PRIVATE KEY-----\n..."
JWT_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n..."
STRIPE_SECRET=sk_test_...
STRIPE_WH_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_TEAM=price_...
BASE_URL=http://localhost:8000
```

### Electron App (`.env`)

```bash
BROUSLA_CLOUD_URL=http://localhost:8000
```

## API Endpoints

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /devices/register` - Register device (Bearer)

### Entitlements

- `GET /entitlements` - Get license JWT (Bearer)
- `GET /pubkey` - Get public key (JWKs) for verification

### Billing

- `POST /billing/create-checkout-session` - Create Stripe checkout (Bearer)
- `POST /billing/create-portal-session` - Create customer portal (Bearer)

### Webhooks

- `POST /stripe/webhook` - Handle Stripe events

### Usage

- `POST /usage/report` - Report usage metrics (Bearer)

## Database Models

### Plans (Seeded)

| Plan  | Price  | Renders/Day | Projects | Quality | Seats |
|-------|--------|-------------|----------|---------|-------|
| FREE  | $0     | 10          | 3        | 720p    | 1     |
| PRO   | $19/mo | 100         | ∞        | 4K      | 1     |
| TEAM  | $49/mo | 500         | ∞        | 4K      | 5     |

### Schema

- `users` - User accounts with Stripe customer ID
- `devices` - Registered devices per user
- `subscriptions` - Active/canceled subscriptions
- `plans` - Available plans with limits
- `entitlements` - Issued license JWTs
- `usage` - Usage metrics for metering

## License JWT Claims

```json
{
  "sub": "123",                    // User ID
  "plan": "PRO",                   // Plan name
  "limits": {
    "max_renders_per_day": 100,
    "max_seats": 1,
    "max_projects": -1,            // -1 = unlimited
    "max_export_quality": "4k"
  },
  "seats": 1,
  "device_max": 3,                 // Max devices
  "exp": 1234567890,               // Expiry (30 days)
  "iat": 1234567890,               // Issued at
  "type": "license"                // Token type
}
```

## Entitlement Checking

```typescript
import { isEntitled } from './utils/license';

// Check render entitlement
const result = await isEntitled('render', currentUsage);
if (!result.entitled) {
  alert(result.reason); // "Daily render limit reached (100)"
  return;
}

// Check 4K export
const result = await isEntitled('export_4k');
if (!result.entitled) {
  alert(result.reason); // "4K export requires PRO or TEAM plan"
  return;
}

// Proceed with feature
doRender();
```

## Usage Reporting

```typescript
import { reportUsage } from './utils/license';
import { getAuthState } from './utils/auth';

const { accessToken } = getAuthState();

// Report render completed
await reportUsage(accessToken, 'render', 1);
```

## Acceptance Criteria

✅ **Fresh Install**
- New user gets FREE plan automatically
- License JWT issued immediately
- Can use app within free limits

✅ **Upgrade Flow**
- User clicks upgrade
- Stripe Checkout opens in browser
- After payment, webhook updates subscription
- `/entitlements` returns PRO license within 10s
- App polls and updates

✅ **Limit Enforcement**
- App blocks over-limit renders
- Shows "Subscription Required" page
- Provides upgrade options

✅ **Cancellation**
- Subscription canceled via Stripe portal
- Webhooks updates status
- User reverts to FREE plan after period end

✅ **Offline Mode**
- Cached license works for 72h after last fetch
- After 72h, requires re-authentication
- Graceful degradation

## Deployment

### Cloud Service

```bash
# Build and push Docker image
docker build -t brousla-cloud:latest ./brousla-cloud
docker tag brousla-cloud:latest your-registry/brousla-cloud:latest
docker push your-registry/brousla-cloud:latest

# Deploy to your cloud (AWS, GCP, etc.)
# Set environment variables
# Run database migrations
# Configure Stripe webhook URL
```

### Electron App

```bash
# Build for distribution
npm run dist

# Output in dist/
# - Brousla-1.0.0.dmg (macOS)
# - Brousla Setup 1.0.0.exe (Windows)
# - Brousla-1.0.0.AppImage (Linux)
```

## Troubleshooting

### Cloud service won't start
- Check DATABASE_URL is correct
- Ensure Postgres is running
- Verify JWT keys are properly formatted

### License verification fails
- Check JWT_PUBLIC_KEY_PEM matches private key
- Ensure keys don't have extra quotes/escapes
- Verify clock sync (JWT exp validation)

### Stripe webhooks not working
- Check STRIPE_WH_SECRET is correct
- Verify endpoint is publicly accessible
- Check Stripe dashboard for failed deliveries

### Offline mode not working
- Check localStorage for cached license
- Verify grace period hasn't expired
- Check browser console for errors

## Security Notes

🔒 **Private Key Security**
- Never commit JWT private key to git
- Use environment variables or secrets manager
- Rotate keys periodically

🔒 **Stripe Webhook Verification**
- Always verify webhook signatures
- Use STRIPE_WH_SECRET from environment
- Log failed verifications

🔒 **Token Storage**
- Store tokens in localStorage (browser)
- Clear on logout
- Don't expose in URLs/logs

## License

ISC

## Support

For issues: https://github.com/clamprou/brousla-app/issues
