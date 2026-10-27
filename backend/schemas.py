from datetime import date, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IndicatorParams(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    period: int = Field(default=14, ge=2, le=250)
    fast_period: int = Field(default=20, ge=2, le=250)
    slow_period: int = Field(default=50, ge=3, le=300)
    signal_period: int = Field(default=9, ge=2, le=100)
    std_dev: float = Field(default=2, gt=0, le=5)


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    indicator: Literal["RSI", "SMA_CROSS", "EMA_CROSS", "MACD", "BOLLINGER"] = "RSI"
    condition: Literal["crosses_below", "crosses_above", "touches_lower", "touches_upper"] = (
        "crosses_below"
    )
    value: float = Field(default=30, ge=0, le=100)
    params: IndicatorParams = Field(default_factory=IndicatorParams)

    @model_validator(mode="after")
    def valid_combination(self):
        if self.indicator == "MACD":
            if "fast_period" not in self.params.model_fields_set:
                self.params.fast_period = 12
            if "slow_period" not in self.params.model_fields_set:
                self.params.slow_period = 26
        if self.indicator == "BOLLINGER" and "period" not in self.params.model_fields_set:
            self.params.period = 20
        if self.indicator == "BOLLINGER":
            if self.condition not in {"touches_lower", "touches_upper"}:
                raise ValueError("Bollinger rules require touches_lower or touches_upper.")
        elif self.condition not in {"crosses_below", "crosses_above"}:
            raise ValueError("This indicator requires a crossing condition.")
        if (
            self.indicator in {"SMA_CROSS", "EMA_CROSS", "MACD"}
            and self.params.fast_period >= self.params.slow_period
        ):
            raise ValueError("Fast period must be less than slow period.")
        return self


class PositionSizing(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["fixed_capital"] = "fixed_capital"
    amount: float = Field(default=100000, gt=0, le=1_000_000_000)


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date = Field(default_factory=lambda: date.today() - timedelta(days=365 * 3))
    end: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end:
            raise ValueError("Start must be earlier than end.")
        if self.start < date(1994, 11, 3):
            raise ValueError(
                "NSE stock backtests require dates on or after 3 November 1994. No synthetic index substitution is performed."
            )
        if self.end > date.today():
            raise ValueError("End date cannot be in the future.")
        return self


class Strategy(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    ticker: str = Field(default="RELIANCE.NS", min_length=1, max_length=30)
    entry_rule: Rule = Field(default_factory=Rule)
    exit_rule: Rule = Field(default_factory=lambda: Rule(condition="crosses_above", value=70))
    position_sizing: PositionSizing = Field(default_factory=PositionSizing)
    stop_loss_pct: float = Field(default=5, ge=0, le=99)
    take_profit_pct: Optional[float] = Field(default=15, ge=0, le=1000)
    cost_bps: float = Field(default=10, ge=0, le=500)
    slippage_bps: float = Field(default=5, ge=0, le=500)
    date_range: DateRange = Field(default_factory=DateRange)
    scenario_label: Optional[str] = Field(default=None, max_length=200)
