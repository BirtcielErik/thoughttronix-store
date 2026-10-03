# CLAUDE.md — The ThoughtTronix Store

A server-rendered Django 6 storefront and back office. The PRD (`prd/core-platform.md`) and the plan (`plans/core-platform.md`) record how the core platform was designed and built.

## Commands

- `uv sync` — install dependencies (Python 3.13, managed by uv)
- `uv run python manage.py migrate` — apply migrations
- `uv run python manage.py seed` — reset the database to the demo world
  (destructive, idempotent)
- `uv run python manage.py tailwind runserver` — dev server + Tailwind watch
- `uv run python manage.py tailwind build` — compile production CSS
- `uv run pytest` — run the test suite
- `uv run ruff check .` and `uv run ruff format .` — lint and format

## Project layout

- `config/` — the project package (settings, root urls)
- `accounts/` — custom user model (`accounts.User`, `AbstractUser` + nullable
  `job_title`). Roles are Django's own vocabulary: customers are plain users,
  employees are `is_staff`, the admin is `is_superuser`. No role field, no Groups.
- `products/` — catalog (`Category`, `Product`, `Tag`), its back-office CRUD,
  and the `seed` command
- `orders/` — cart, checkout, orders, and back-office order management
- `coupons/` — `Coupon` (percent or fixed amount, order-wide or one
  product — a fixed amount on a product comes off each unit; retired,
  never deleted), its rules (`Coupon.discount_for`), and
  the back-office Coupons tab. `orders` imports `coupons`, never the reverse.
- `dashboard/` — the staff analytics dashboard
- `PROMPTS.md` — the AI-usage log; append entries, never rewrite history
- `templates/` — project-level templates (`base.html`); app templates live in
  `templates/<app>/`
- `assets/` — static sources; `assets/css/source.css` is the Tailwind input,
  `assets/css/tailwind.css` is compiled output (gitignored, never edit)

## Architecture and URL convention

Before touching models, views, services, settings, or adding or changing URLs, read `docs/ARCHITECTURE.md`.

## Template conventions

Before touching templates, HTMX, or styling, read `docs/FRONTEND.md`.

## Testing

Before writing or changing tests, read `docs/TESTING.md`.