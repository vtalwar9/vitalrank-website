# ViTalRank Website Audit — vitalrank.netlify.app

**Date:** September 17, 2026
**Scope:** All 17 live pages (home, about, services, contact, blog listing, 6 service pages, 6 blog posts) + 404 handling
**Method:** Automated crawl of every page — every link clicked programmatically, every tag inspected

**Bottom line:** The site is solid structurally — no broken pages, fast, clean code. But there are 4 critical issues hurting you on Google, all fixable in one sitting.

---

## 🔴 CRITICAL — fix these first

### 1. Broken links sitting in your footer on every page
- **What:** Each footer column ("Company", "Pages", "Services") contains a dead link that goes to `/{{url}}` — a leftover placeholder from the template that was never filled in. It leads to a 404 error page.
- **Where:** All 17 pages, footer, one per column (3 dead links per page = 51 total)
- **Why it matters:** Google penalizes sites with broken links, and if a visitor ever taps one they hit an error page. It also looks unfinished to anyone who inspects the site.
- **Fix:** Delete the three placeholder links (or fill them with real links).

### 2. No sitemap.xml — Google can't find all your pages efficiently
- **What:** `https://vitalrank.netlify.app/sitemap.xml` returns a 404. There is no sitemap at all.
- **Why it matters:** A sitemap is the map you hand Google listing every page. Without it, Google discovers pages slowly and may miss your blog posts entirely. For an SEO agency, this is the one thing you can't be missing.
- **Fix:** Generate a sitemap with all 17 pages and reference it in robots.txt.

### 3. No canonical tags on any page
- **What:** Not a single page has a canonical tag (checked all 17).
- **Why it matters:** The canonical tag tells Google "this is the official address of this page." Without it, `vitalrank.netlify.app/about-us` and `vitalrank.netlify.app/about-us/` look like two different pages to Google, splitting your ranking power.
- **Fix:** Add one line per page pointing to its own full URL.

### 4. Link previews are broken when anyone shares your site
- **What:** 16 of 17 pages have no Open Graph tags at all, and **no page** has a preview image set. Only the homepage has a share title/description.
- **Where:** About, Services, Contact, Blog, all 6 service pages, all 6 blog posts
- **Why it matters:** When someone pastes your link into WhatsApp, LinkedIn, Twitter, or iMessage, it shows up as a sad grey box with no image instead of a proper card with your branding. You're losing clicks every time a link is shared.
- **Fix:** Add OG title, description, and image tags to every page.

---

## 🟡 IMPORTANT — fix these next

### 5. Your footer links to a "404" page
- **What:** The "Pages" footer column contains a visible link labeled **404** pointing to `/404/`.
- **Why it matters:** No visitor should ever be one click from an error page. It looks like a mistake (because it is one).
- **Fix:** Remove it.

### 6. Footer service names don't match your services
- **What:** The "Services" footer column lists **Market research**, **Strategic planning**, and **Financial advisory** — but they link to your SEO Consulting, Technical SEO, and Enterprise SEO pages. The names are leftovers from the consulting template and describe the wrong thing. Also, only 3 of your 6 services are listed (Local SEO, Ecommerce SEO, and B2B SEO are missing).
- **Why it matters:** A visitor looking for "Local SEO" won't find it in the footer, and "Financial advisory" linking to an SEO page is confusing and unprofessional.
- **Fix:** Rename to your actual 6 service names and link each correctly.

### 7. Social icons link to fake placeholder profiles
- **What:** The Facebook, Twitter/X, Instagram, and YouTube icons in the footer link to `facebook.com/facebook`, `twitter.com`, `instagram.com/instagram/`, `youtube.com/youtube` — generic placeholders, not your accounts.
- **Why it matters:** Clicking your Facebook icon takes visitors to a random Facebook page. Either connect your real profiles or remove the icons until you have them.
- **Fix:** Replace with your real profile URLs (or remove the icons for now).

### 8. Homepage description is too long for Google
- **What:** Your homepage meta description is 194 characters. Google shows ~155, so yours gets cut off mid-sentence: *"…ViTalRank is your trusted partner for advanced SEO consulting services, AI-driven SEO strategies, and digital growth solutions. Improve search rankings, drive targeted traffic, and maximize ROI."*
- **Why it matters:** The cut-off looks sloppy in search results and wastes the most valuable sentence on your most valuable page.
- **Fix:** Trim to under 160 characters.

### 9. Blog post titles get cut off in Google
- **What:** All 6 blog post titles are 64–67 characters (e.g. *"The importance of good leadership in a growing business | ViTalRank"*). Google displays ~60.
- **Why it matters:** Minor, but your headlines get truncated in search results.
- **Fix:** Shorten the "| ViTalRank" suffix or tighten titles.

### 10. Contact page has no email or phone number
- **What:** The contact page (`/contact/`) has only a form — no email address, no phone number anywhere on the page (or in the footer).
- **Why it matters:** Many visitors won't fill out a form; they want to email or call directly. Every extra step loses you leads. It also looks less trustworthy for an agency.
- **Fix:** Add your email and phone to the contact page and footer.

### 11. Footer has no copyright line or contact info
- **What:** The footer ends after the link columns — no "© 2026 ViTalRank", no address, email, or phone.
- **Why it matters:** Looks incomplete, and a copyright line + contact details are small trust signals every business site has.
- **Fix:** Add one footer bottom row with copyright and contact details.

### 12. Google-friendly code (schema) exists on only 1 of 17 pages
- **What:** Only the homepage has Organization schema markup. The other 16 pages have none — no LocalBusiness info, no article markup on blog posts.
- **Why it matters:** Schema is how you get rich results on Google (star ratings, business info panels, article carousels). Your competitors likely have it.
- **Fix:** Add relevant schema to about, contact, service, and blog post templates.

### 13. Blog posts show 2022 dates
- **What:** Blog posts display old dates (e.g. "Feb 28, 2022").
- **Why it matters:** Visitors (and Google) see 4-year-old dates and assume the content — and the business — is stale.
- **Fix:** Update post dates or remove date display.

---

## 🟢 NICE-TO-HAVE — polish items

- **Short descriptions on 4 pages:** About (117 chars), Contact (101), Blog listing (99), and 2 blog posts (116) are under the ideal 120–160 range. Not broken, just under-optimized.
- **Homepage hero image is 312 KB** (`/assets/img/home-hero.jpg`, 2112×1168). It loads fine, but compressing it would make phones load the page noticeably faster.
- **Blog posts don't link to your services in the article text.** Adding 1–2 natural links per post (e.g. a post about strategy → your SEO consulting page) is one of the highest-ROI SEO moves for blogs.
- **No breadcrumbs** on service/blog pages (e.g. Home → Services → Technical SEO). Helps visitors and Google understand your site structure.
- **`/admin/` (your CMS login) is publicly reachable** — that's normal and required for the CMS to work, and robots.txt already tells Google not to index it. Just make sure your GitHub login stays secure.
- **Mobile menu** couldn't be click-tested in this audit (no browser). The code for it is present and correct — worth one manual tap-through on your phone.

---

## ✅ What's already good (no action needed)

- **All 17 pages load correctly** — zero broken pages, proper 404 status on bad URLs
- **Header is identical on every page** — logo, nav (Home / About / Services / Blog), and Contact button all correct
- **Every page has exactly one H1**, all unique and keyword-relevant
- **All page titles unique**; all meta descriptions present and unique
- **All images have alt text** (11/11 on homepage)
- **http automatically goes to https**; trailing slashes consistent
- **Favicon present**; page language set; proper 404 page with "noindex"
- **Contact page is linked from every page** (header button) — good conversion coverage
- **No mixed-content issues**; total homepage weight (~1 MB images) is reasonable
- **No broken anchor (`#`) links** anywhere on the site

---

## Recommended fix order

1. Delete the 3 footer placeholder links (30 min)
2. Add sitemap.xml + reference in robots.txt (30 min)
3. Add canonical tags to all pages (30 min)
4. Add OG tags + share image to all pages (1 hr)
5. Fix footer: remove 404 link, correct service names, add all 6 services (30 min)
6. Connect real social profiles or remove icons (15 min)
7. Trim homepage meta description; shorten blog titles (20 min)
8. Add email/phone to contact page + footer; add copyright line (30 min)
9. Add schema markup to remaining templates (1 hr)
10. Update blog dates (15 min)

Items 1–4 are the ones costing you Google visibility today. Everything else is polish.
