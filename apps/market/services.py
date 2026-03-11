from apps.market.models import MarketSnapshot


def normalize_market_snapshot(stock_code: str, payload: dict) -> dict:
    raise NotImplementedError


def upsert_market_snapshot(snapshot_data: dict) -> MarketSnapshot:
    raise NotImplementedError


def collect_market_snapshots(stock_codes: list[str] | None = None) -> dict:
    raise NotImplementedError


def to_prompt_fields(snapshot: MarketSnapshot) -> dict:
    raise NotImplementedError
