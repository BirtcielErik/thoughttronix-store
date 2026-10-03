# Architecture

## Architecture convention

Logic lives in models and managers; cross-model workflows get a service
module; views stay thin.

Exactly two deliberate deep modules, docstrings and type hints on every
public function: `orders/services.py` (`place_order`, whose `coupon_code`
is checked there as the final authority) and `dashboard/queries.py` (the
dashboard's aggregations).

Idiomatic Django throughout: class-based views, model methods, custom
managers/querysets, forms own their validation. Settings read from `.env`
via environs with working defaults — the app must run with no `.env` present.

## URL conventions

- Every URL is named; every app has a namespace (`products:catalog`,
  `orders:checkout`).
- Public catalog URLs use slugs (`/products/seraphine-home-hub/`);
  back-office URLs use pks.
- `Product` defines `get_absolute_url`.
