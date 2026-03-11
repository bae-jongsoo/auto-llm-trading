from apps.dart.models import DartDisclosure


def upsert_disclosures(stock_code: str, corp_code: str, rows: list[dict]) -> list[DartDisclosure]:
    raise NotImplementedError


def collect_dart(stock_codes: list[str] | None = None) -> dict:
    raise NotImplementedError
