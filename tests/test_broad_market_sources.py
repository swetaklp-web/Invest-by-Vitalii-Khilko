from app.sources import barchart, yahoo


def test_yahoo_discovery_covers_multiple_market_domains() -> None:
    queries = " ".join(yahoo.DISCOVERY_QUERIES).lower()

    for domain in ("bank", "healthcare", "energy", "industrial", "consumer", "materials", "small cap"):
        assert domain in queries


def test_barchart_watchlist_is_not_technology_only() -> None:
    required = {"XLF", "XLV", "XLE", "XLI", "XLY", "XLU", "XLRE", "XLB", "IWM"}

    assert required.issubset(set(barchart.WATCHLIST))


def test_yahoo_sector_discovery_covers_all_major_sector_etfs() -> None:
    required = {"XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLRE", "XLB", "XLK", "XLC"}

    assert required.issubset(set(yahoo.SECTOR_DISCOVERY_SYMBOLS))
