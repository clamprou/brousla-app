# Quick Start Guide

Get Brousla up and running in 5 minutes!

## Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+ (for cloud service)
- Stripe account (test mode)

## Step 1: Start Cloud Service (2 min)

```bash
cd brousla-cloud

# Generate JWT keys
python3 scripts/generate_keys.py > keys.txt

# Setup environment
cp .env.example .env

# Edit .env - paste keys from keys.txt
# Add your Stripe test keys from https://dashboard.stripe.com/test/apikeys
nano .env

# Start services
docker-compose up -d

# Wait for services to be healthy (~30s)
docker-compose ps

# Test
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

## Step 2: Setup Stripe (1 min)

```bash
# Install Stripe CLI (if not already installed)
# macOS: brew install stripe/stripe-cli/stripe
# Windows: scoop install stripe
# Linux: See https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local
stripe listen --forward-to localhost:8000/stripe/webhook

# Copy the webhook secret (whsec_...) to .env
# STRIPE_WH_SECRET=whsec_...

# In another terminal, create products
stripe products create --name="Brousla PRO" --description="Professional plan"
# Copy product ID

stripe prices create \
  --product=prod_... \
  --unit-amount=1900 \
  --currency=usd \
  --recurring[interval]=month

# Copy price ID to .env as STRIPE_PRICE_ID_PRO

# Repeat for TEAM plan ($49)
stripe products create --name="Brousla TEAM" --description="Team plan"
stripe prices create \
  --product=prod_... \
  --unit-amount=4900 \
  --currency=usd \
  --recurring[interval]=month

# Copy price ID to .env as STRIPE_PRICE_ID_TEAM

# Restart cloud service to load new env vars
docker-compose restart api
```

## Step 3: Start Electron App (2 min)

```bash
cd ..  # Back to root

# Install dependencies
npm install

# Setup environment
cp .env.example .env
# Edit if needed (default is fine for local dev)

# Start development mode
npm run electron-dev

# App will open in ~30s
```

## Step 4: Test It! (5 min)

### Test 1: Local Dev Mode (No Cloud)

1. App opens → Click "Use Local Dev Mode"
2. Enter any email → Click "Sign In"
3. ✅ App should open (no cloud connection needed)

### Test 2: Cloud Registration

1. Restart app → Enter real email + password
2. Click "Create Account"
3. ✅ App should open after registration

### Test 3: Check Entitlements

1. Click "Check Render Entitlement" button
2. ✅ Should show: "✓ Entitled to render (0/10)"

### Test 4: Upgrade to PRO

1. Click "Account" in top nav
2. Click "Manage Billing" (if not available, logout and login with cloud mode)
3. Or force upgrade flow:
   - Logout
   - Close app
   - Open app → Login with cloud
   - You'll see "Subscription Required" page
4. Click "Upgrade to PRO"
5. Stripe Checkout opens in browser
6. Use test card: `4242 4242 4242 4242`
7. Complete checkout
8. ✅ Webhook fires → Subscription created
9. Close Stripe page → Back to app
10. Refresh app (or poll `/entitlements`)
11. ✅ Should now have PRO features

### Test 5: Offline Mode

1. Login with cloud mode
2. Stop cloud service: `docker-compose down`
3. Restart app
4. ✅ Should still work (cached license, 72h grace)

## Troubleshooting

### Cloud service won't start
```bash
# Check logs
docker-compose logs api

# Common issues:
# - Database not ready → wait 30s
# - Port 8000 in use → change in docker-compose.yml
# - Invalid keys → regenerate with generate_keys.py
```

### Electron app won't start
```bash
# Check Node version
node -v  # Should be 18+

# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check port
# React dev server uses 3000
# If in use, kill process: lsof -ti:3000 | xargs kill
```

### Stripe webhooks not working
```bash
# Ensure stripe CLI is running
stripe listen --forward-to localhost:8000/stripe/webhook

# Test webhook manually
stripe trigger customer.subscription.created

# Check cloud service logs
docker-compose logs -f api
```

## Next Steps

- Read full [README.md](./README.md) for architecture details
- Explore API docs: http://localhost:8000/docs
- Build your features!
- Add entitlement checks before premium features
- Report usage metrics
- Deploy to production

## Test Cards

Use these Stripe test cards:

| Card Number | Result |
|------------|--------|
| 4242 4242 4242 4242 | Success |
| 4000 0002 5000 0000 | Requires authentication |
| 4000 0000 0000 0002 | Declined |

Any future expiry date, any 3-digit CVC.

## Support

Issues? Check:
- http://localhost:8000/docs for API
- docker-compose logs for errors
- Browser console for client errors

Happy coding! 🚀
