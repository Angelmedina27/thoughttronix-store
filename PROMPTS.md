# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-09-19 — Add `is_featured` to Product, badge it in templates, recover admin access

### Prompts
1. Look at the Product model in `products/models.py` and add a new boolean field named `is_featured`. It should default to `False` so existing products stay unfeatured. Do not add any badges or modify templates yet.
2. Please generate the database migration files for the products app and apply them to the database.
3. Please update the frontend templates to display a "Featured" badge for any product where `is_featured` is `True`. The badge must appear in two places: on the main catalog listing page and on the individual product detail page. Match the existing styling patterns used in the templates.
4. `uv run python manage.py tailwind runserver`
5. I am locked out of the Django admin panel at `/admin/`. Can you list the usernames of the superusers or staff accounts currently in the database? If there isn't one I can use, please create a new superuser with the username `admin` and password `admin123`.
6. The `/admin/` web interface is not loading correctly. Can you use a Django shell command or python script to programmatically set `is_featured=True` for the three products: `Seraphine`, `SoulSear Mark II`, and `SoulSear Mark I` and save them directly to the database?
7. Append a session log to `PROMPTS.md` at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections.

### Summary
- **Outcome:** Added `Product.is_featured` (`BooleanField`, `default=False`) in `products/models.py`; generated and applied migration `products/migrations/0003_product_is_featured.py`. Added a "Featured" badge (`badge-primary badge-outline`, matching existing badge conventions) to `templates/products/catalog.html` and `templates/products/detail.html`, shown only when `product.is_featured` is true. Started the Tailwind dev server in the background. Set `is_featured=True` on Seraphine, SoulSear Mark I, and SoulSear Mark II via a Django shell one-off script (bypassing the broken `/admin/` UI), matched by exact product name and saved with `update_fields=['is_featured']`.
- **Deviations:** On prompt 5, a superuser named `admin` already existed in the database, so the assistant did not create a new one as literally requested — it surfaced the existing `admin` (superuser) and `employee` (staff) accounts instead and asked how to proceed (reset `admin`'s password to `admin123`, reset to a different password, or do nothing). The user chose to do nothing, so no credentials were changed and the original admin lockout was not resolved.
- **Sideways:** The admin lockout from prompt 5 was never actually fixed — the user declined all offered remedies, so whoever is locked out of `/admin/` still is. The `is_featured` flags on the three named products were set directly via shell script as a workaround for the same broken `/admin/` UI, rather than through the admin panel or a form.
