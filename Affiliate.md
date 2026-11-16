# Affiliate program

We set up every affiliate ourselves. Each affiliate gets a unique code, a revenue share (percentage of what
their referred users pay), and optionally a discount for the users they refer. Payouts are manual.

- Backend: `backend/services/affiliates.py`, endpoints in `backend/main.py`, Stripe hooks in `backend/services/billing.py`
- Frontend: `frontend/src/lib/referral.js`, signup field in `frontend/src/pages/AuthPage.jsx`, prices in `AccountSettingsPage.jsx`
- Database: `supabase/migrations/20261116000000_affiliates.sql` (applied to prod 2026-11-15)

## How it works

1. **We create the affiliate** with the admin API (below) and give them their link or code.
2. **A user signs up with the code**, either by:
   - opening a referral link: `https://bankstatementscanner.com/?ref=<code>` (works on any app or marketing
     page; the code is remembered in the browser for 30 days), or
   - typing it into the **Referral code (optional)** field on the signup form. The form checks the code as they
     type and shows the discount it gives.
3. **The code is attached to the account** on its first sign-in (`POST /api/referral/claim`). Rules:
   - only accounts under 7 days old can claim, so existing users can't be attached later
   - first code wins; an account belongs to one affiliate, permanently
   - inactive or unknown codes are ignored
4. **Every payment by that user earns the affiliate a commission**, recorded by the Stripe webhook:
   - monthly plan invoices and page-pack purchases both count
   - commission = amount paid **before tax** × the affiliate's `revenue_share_pct` at that moment
   - free / trial (`$0`) invoices earn nothing
   - Stripe retrying a webhook never records the same payment twice
   - if `commission_months` is set, only payments within that many months of the user's signup count
5. **We pay the affiliate** outside the app, then mark their pending commissions as paid.

### Referral discount (optional)

An affiliate can carry a discount for the users they refer:

- **Monthly plan:** `discount_pct` off for `discount_months` months, counted from when the user subscribes
  (omit `discount_months` for forever). Only their first subscription gets it. The backend creates a Stripe coupon
  for the affiliate automatically and reuses it.
- **Page packs** (if `discount_packs` is `true`): the same percentage off while the user is within
  `discount_months` of signing up. A pack never costs less than $0.50 (Stripe's minimum charge).
- The Account page shows referred users their discounted plan and pack prices.
- Discounted checkouts don't show Stripe's promo-code box; Stripe allows a discount or promo codes, not both.
- **Commission is on what the user actually paid**, so the discount comes out of the affiliate's share.
  Example: 25% off the $10 plan with a 20% revenue share → user pays $7.50, affiliate earns $1.50.
- Changing an affiliate's discount affects new subscriptions only; existing subscribers keep the coupon they got.

## Creating an affiliate

All admin endpoints need `API_AUTH_SECRET` (the same secret the daily blog job uses; it's in the Render
environment variables and `backend/.env`).

```bash
export API=https://pdf-reading-agent.onrender.com
export API_AUTH_SECRET='<your secret>'

curl -X POST $API/admin/affiliates \
  -H "Authorization: Bearer $API_AUTH_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "email": "jane@example.com",
    "code": "jane",
    "revenue_share_pct": 20,
    "commission_months": 12,
    "discount_pct": 25,
    "discount_months": 3,
    "discount_packs": true
  }'
```

The response includes the affiliate's `id`. Keep it: you need it to edit their terms or record payouts.

Then give the affiliate either their link, `https://bankstatementscanner.com/?ref=jane`, or the code `jane`.

### Fields

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Affiliate's name, for our records |
| `code` | yes | 3–32 characters: letters, digits, `-` or `_`. Stored lowercase. Must be unique (a taken code returns `409`) |
| `revenue_share_pct` | yes | Percent of each payment by their referrals that we owe them (0–100) |
| `email` | no | Their contact email |
| `commission_months` | no | How many months after a user's signup the affiliate earns on that user's payments. Omit for lifetime |
| `discount_pct` | no | Percent off for users they refer. Default `0` = no discount |
| `discount_months` | no | Discount length: plan counts from subscribing, packs from signup. Omit for forever |
| `discount_packs` | no | `true` to also discount page packs. Default `false` |
| `notes` | no | Free text for ourselves |

## Managing affiliates

```bash
AUTH="Authorization: Bearer $API_AUTH_SECRET"

# List all affiliates with signups (referrals), referred revenue, and commission
# pending / paid (all money in cents)
curl $API/admin/affiliates -H "$AUTH"

# Change terms. A new revenue_share_pct applies to future payments only.
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"revenue_share_pct": 25}'

# Add or change the discount for referred users
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"discount_pct": 10, "discount_months": 1}'

# Deactivate: the code stops working for new signups, and no new commission or discount applies
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"active": false}'
```

Editable fields: `name`, `email`, `revenue_share_pct`, `commission_months`, `discount_pct`, `discount_months`,
`discount_packs`, `active`, `notes`. The `code` can't be changed; create a new affiliate instead.

## Paying affiliates

```bash
# See what we owe (status: pending | paid | void; omit for all)
curl "$API/admin/affiliates/<id>/commissions?status=pending" -H "$AUTH"

# After paying them, mark all pending commissions up to now as paid
curl -X POST $API/admin/affiliates/<id>/payouts -H "$AUTH" -H "Content-Type: application/json" -d '{}'

# Or only those up to a cutoff (e.g. end of last month)
curl -X POST $API/admin/affiliates/<id>/payouts -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"before": "2026-11-30T23:59:59Z"}'
```

The payout call returns how many commissions were marked paid and their total in cents.

## Refunds

Refunds and chargebacks are not handled automatically. If a referred user is refunded, void the commission
in the Supabase SQL editor using the Stripe invoice or checkout session id:

```sql
UPDATE affiliate_commissions SET status = 'void' WHERE source_id = '<stripe invoice or checkout session id>';
```

## Not built yet

- Automatic refund / chargeback handling
- A dashboard for affiliates to see their own referrals and earnings (share numbers from the admin list for now)
- An admin UI (everything is done through the API calls above)
