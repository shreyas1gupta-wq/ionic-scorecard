# Getting it online — the parts only you can do

Two free accounts. No card, no monthly cost. Roughly 30 minutes of clicking.

Do these in order. **Nothing here is irreversible** — both accounts can be deleted afterwards and neither asks for payment details.

---

## Before you start: one rule about the database password

Step 1 gives you a **database password / connection string**. It is the key to everything in the app.

**Do not paste it into a chat, an email, a document, or a message to me.** You will store it yourself, in step 4, with a single command that sends it straight to Cloudflare. I never need to see it, and anything I can see ends up in a transcript.

If you accidentally reveal it: Supabase lets you reset the database password from the same settings page. Do that rather than hoping.

---

## Step 1 — Supabase (the database)

1. Go to **supabase.com** → *Start your project* → sign in with GitHub or email.
2. Create a **New project**.
   - **Name**: `ionic-crm`
   - **Database password**: click *Generate a password* and let the browser save it. You will not need to type it again.
   - **Region**: ⚠ **choose South Asia (Mumbai) `ap-south-1` if it appears in the list.**
3. **Write down whether Mumbai was actually offered on the free plan.** This is the one fact I could not verify from documentation, and it is the only thing that decides whether the data sits in India. If Mumbai is greyed out or absent, pick Singapore and tell me — it still works, it just changes what we can honestly claim about where the data lives.
4. Wait ~2 minutes for the project to finish building.
5. Go to **Project Settings → Database**. Find the **Connection string** section. Leave that tab open for step 4 — do not copy it anywhere else yet.

**Also worth knowing:** a free Supabase project **pauses itself after about a week with no activity**, and you resume it with one click in the dashboard. Once colleagues are using it daily that never happens; during a quiet week it might.

---

## Step 2 — Cloudflare (the hosting and the login)

1. Go to **cloudflare.com** → *Sign up* → verify your email. Do **not** add a payment method; you do not need one.
2. You do **not** need to buy a domain and you do **not** need to change anything about `ionic.in`. The app will live at a free `*.pages.dev` style address. This is deliberate — it means no DNS request to IT.

---

## Step 3 — Cloudflare Access (how people sign in)

This is the part that means **no passwords anywhere**. Colleagues type their work email, Cloudflare emails them a 6-digit code, they type it in. Cloudflare sends that email from its own systems, so nothing has to be configured on `ionic.in`.

1. In the Cloudflare dashboard, open **Zero Trust** (left sidebar). Complete the short first-time setup — when it asks you to **choose a team name**, pick something like `ionic` and **write it down**; it becomes `ionic.cloudflareaccess.com` and I need it.
2. When asked to choose a plan, choose **Free**.
3. **While you are here, note the seat count.** Go to **Settings → Billing** (or the plan page) and write down **how many free seats you have**. Marketing says 50, one page suggested no limit, and I could not settle it. This matters because if you have fewer seats than people, colleagues get *blocked at login* rather than billed.
4. Go to **Settings → Authentication → Login methods** and add **One-time PIN** if it is not already listed. In newer accounts it is not enabled by default.

Stop there. The actual *application* in Access has to be created after the app is deployed, because it needs the address — I will walk you through that step when we get to it, and it produces one more value I need (an "Application Audience tag").

---

## Step 4 — Hand the database password to Cloudflare, without it passing through anyone

Once I have prepared the deployment (I am working on that now), you will run **one command** in the terminal. It will look like this:

```
npx wrangler secret put CRM_DATABASE_URL
```

It prompts you to paste the connection string. It goes straight from your clipboard into Cloudflare's encrypted secret store. It is not written to any file in the project, it is not visible in the Cloudflare dashboard afterwards, and it never appears in our conversation.

Two more, the same way, using the values you wrote down:

```
npx wrangler secret put CRM_ACCESS_TEAM_DOMAIN
npx wrangler secret put CRM_ACCESS_AUD
```

---

## What to tell me when you're done

Just these four things — none of them secret:

| | |
|---|---|
| 1 | Was **Mumbai** offered on the Supabase free plan? |
| 2 | Your Cloudflare **team name** (the `something.cloudflareaccess.com` part) |
| 3 | How many **free Access seats** you have |
| 4 | Anything that looked different from the steps above |

**Do not send** the database password, the connection string, or any API token.

---

## What happens after that

I finish the piece that lets the app talk to a real database, deploy it, and then walk you through creating the Access application — which is when it becomes a real URL your colleagues can open.

Then the sequence is:
1. You and I check it works.
2. **Three colleagues, two weeks, real tickets.** Not a demo to an audience — actual use. Real users find the awkward parts in the workflow that neither of us can see from here, and that is the entire point.
3. Decide from what they say whether it earns more investment.

## One thing to decide before colleagues use it

Right now the app has a **holiday calendar with four dates in it as placeholders** and **four made-up staff accounts** (Admin User, Priya Manager, Alice Analyst, Bob Associate). Before a real pilot you will want the actual public holidays for the year and the actual three people. Both are editable from the admin screen once you're in — no code needed.
