"""Compatibility entry points for provider-backed fund research."""

from services.supply_chain import get_company_supply_chain


def is_supply_chain_irrelevant(ticker, profile=None):
    return bool(profile and profile.get("instrument_type") in {"ETF", "MUTUALFUND"})


def get_value_ecosystem(ticker, profile=None):
    return get_company_supply_chain(ticker)
