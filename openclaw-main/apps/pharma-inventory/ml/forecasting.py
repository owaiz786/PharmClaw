"""
Demand forecasting for pharmacy inventory.
Uses: moving average (baseline) + linear regression (ML) for 7-day ahead forecast.
Falls back to moving average when not enough data.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def get_daily_sales(db, medicine_id: int, days: int = 30) -> List[int]:
    """Return list of daily sales quantities for the last N days."""
    from db.models import StockTransaction
    from sqlalchemy import func

    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            func.date(StockTransaction.transacted_at).label("day"),
            func.sum(StockTransaction.quantity).label("qty"),
        )
        .filter(
            StockTransaction.medicine_id == medicine_id,
            StockTransaction.transaction_type == "OUT",
            StockTransaction.transacted_at >= cutoff,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    # Fill missing days with 0
    qty_by_day = {r.day: r.qty for r in rows}
    result = []
    for i in range(days, 0, -1):
        d = (datetime.utcnow() - timedelta(days=i)).date()
        result.append(qty_by_day.get(str(d), 0))
    return result


def moving_average_forecast(sales: List[int], horizon: int = 7, window: int = 7) -> List[float]:
    if len(sales) < window:
        avg = statistics.mean(sales) if sales else 0
        return [avg] * horizon
    recent = sales[-window:]
    avg = statistics.mean(recent)
    return [avg] * horizon


def linear_regression_forecast(sales: List[int], horizon: int = 7) -> List[float]:
    """Simple OLS linear regression forecast."""
    n = len(sales)
    if n < 5:
        return moving_average_forecast(sales, horizon)

    xs = list(range(n))
    ys = sales
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(ys)

    numer = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return [y_mean] * horizon

    slope = numer / denom
    intercept = y_mean - slope * x_mean

    predictions = []
    for i in range(1, horizon + 1):
        pred = intercept + slope * (n + i)
        predictions.append(max(0.0, pred))   # no negative demand
    return predictions


def forecast_medicine(db, medicine_id: int, horizon: int = 7) -> Dict:
    """Return full forecast dict for one medicine."""
    sales = get_daily_sales(db, medicine_id, days=30)
    ma_forecast = moving_average_forecast(sales, horizon)
    lr_forecast = linear_regression_forecast(sales, horizon)

    # Blend: 60% LR + 40% MA (LR is better at trends, MA at stable demand)
    blended = [0.6 * lr + 0.4 * ma for lr, ma in zip(lr_forecast, ma_forecast)]

    total_7d = round(sum(blended))
    avg_daily = round(sum(blended) / horizon, 1)

    return {
        "medicine_id": medicine_id,
        "horizon_days": horizon,
        "avg_daily_demand": avg_daily,
        "forecast_7d_total": total_7d,
        "daily_forecast": [round(v, 1) for v in blended],
        "historical_30d": sales,
        "ma_forecast": [round(v, 1) for v in ma_forecast],
        "lr_forecast": [round(v, 1) for v in lr_forecast],
    }


def get_reorder_suggestions(db) -> List[Dict]:
    """Return all medicines that need reordering based on forecast."""
    from db.models import Medicine

    medicines = db.query(Medicine).all()
    suggestions = []

    for med in medicines:
        fc = forecast_medicine(db, med.id)
        days_cover = (med.current_stock / fc["avg_daily_demand"]) if fc["avg_daily_demand"] > 0 else 999
        needs_reorder = med.current_stock <= med.reorder_level or days_cover < 7

        suggestions.append({
            "medicine_id": med.id,
            "name": med.name,
            "current_stock": med.current_stock,
            "reorder_level": med.reorder_level,
            "avg_daily_demand": fc["avg_daily_demand"],
            "days_of_cover": round(days_cover, 1),
            "forecast_7d": fc["forecast_7d_total"],
            "suggested_order_qty": med.reorder_qty if needs_reorder else 0,
            "needs_reorder": needs_reorder,
            "unit": med.unit,
        })

    suggestions.sort(key=lambda x: x["days_of_cover"])
    return suggestions
