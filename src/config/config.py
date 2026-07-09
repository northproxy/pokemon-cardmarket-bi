"""
Configuration loading for the PCIT pipeline.

Scope note: this currently exposes only PIPELINE_TIMEZONE, since that's what
Phase 0a needs. DATABASE_URL, FTP_*, and CARDMARKET_*_URL will be added here
as later phases actually need them, rather than being stubbed out
speculatively ahead of time.
"""
import os

from dotenv import load_dotenv

# Loads .env for local runs. In GitHub Actions there is no .env file, so this
# is a no-op there and the real secrets/variables configured on the repo are
# used directly. load_dotenv() never overwrites a variable that is already
# set in the environment, so this call is safe in both contexts.
load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            f"Check your local .env file (see .env.example), or, in "
            f"GitHub Actions, the repository's configured secrets/variables."
        )
    return value


# PIPELINE_TIMEZONE=Europe/Vienna is a required, explicit setting per
# 02-data-model.md, 04-etl-pipeline-design.md, and 07-github-actions-logic.md:
# snapshotDate / catalogArchiveDate must always be computed in the
# Europe/Vienna timezone, for every run including manual reruns and
# backfills — never inferred from a runner's local clock (GitHub Actions
# runners default to UTC). There is deliberately no hardcoded fallback here:
# if this variable isn't set, that is a configuration bug that should fail
# loudly and immediately, not get silently patched over with an assumed
# default.
PIPELINE_TIMEZONE = _require_env("PIPELINE_TIMEZONE")

# Added for the daily price guide download (src/ingestion).
#
# NAMING NOTE (see DECISIONS.md §7): the real, already-tested FTP
# credentials use FTP_PASS / FTP_REMOTE_DIR, not the FTP_PASSWORD /
# FTP_REMOTE_PATH names used in 06-github-repository-structure.md,
# 07-github-actions-logic.md, and 11-local-environment-setup.md. This code
# follows the real, working credential names. The docs should be corrected
# to match rather than the other way around — this is the second such
# doc-vs-reality gap found during implementation (see DECISIONS.md §3 for
# the first, the FTP folder layout).
#
# CARDMARKET_PRICE_GUIDE_URL now has a default, since the real URL is known
# and isn't sensitive: https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json
# It can still be overridden via env var/secret if Cardmarket ever changes it.
CARDMARKET_PRICE_GUIDE_URL = os.environ.get(
    "CARDMARKET_PRICE_GUIDE_URL",
    "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json",
)
FTP_HOST = _require_env("FTP_HOST")
FTP_USER = _require_env("FTP_USER")
FTP_PASS = _require_env("FTP_PASS")
FTP_REMOTE_DIR = _require_env("FTP_REMOTE_DIR")
