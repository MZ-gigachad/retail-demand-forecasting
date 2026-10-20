"""Indian holiday and festival calendar generator."""
import logging
from typing import Union
import holidays
import pandas as pd
from src.config import CFG, EXTERNAL_DIR

logger = logging.getLogger(__name__)

FIXED = {
    (1, 1): "New Year",
    (1, 26): "Republic Day",
    (8, 15): "Independence Day",
    (10, 2): "Gandhi Jayanti",
    (12, 25): "Christmas",
}

MAJOR_FESTIVALS = {
    "Diwali",
    "Holi",
    "Dussehra",
    "Eid",
    "Christmas",
    "Pongal",
    "Onam",
    "Ganesh Chaturthi",
    "Bakrid",
    "Republic Day",
    "Independence Day",
}


def build_holiday_calendar(
    start: Union[str, pd.Timestamp], end: Union[str, pd.Timestamp]
) -> pd.DataFrame:
    """Build daily Indian holiday and festival calendar with pre-festival windows."""
    dates = pd.date_range(start, end, freq="D")
    years = range(dates.min().year, dates.max().year + 1)

    names = {pd.Timestamp(d): n for d, n in holidays.India(years=years).items()}
    custom_path = EXTERNAL_DIR / "holidays_india.csv"
    if custom_path.exists():
        custom = pd.read_csv(custom_path, parse_dates=["date"])
        for d, n in zip(custom["date"], custom["name"]):
            names[pd.Timestamp(d)] = n

    for d in dates:
        fixed_name = FIXED.get((d.month, d.day))
        if fixed_name and d not in names:
            names[d] = fixed_name

    cal = pd.DataFrame({"Date": dates})
    cal["Holiday_Name"] = cal["Date"].map(names)
    cal["Holiday"] = cal["Holiday_Name"].notna().astype("int8")

    window = (
        CFG.get("adaptation", {})
        .get("festival_uplift", {})
        .get("window_days", 7)
    )
    cal["Festival_Window"] = 0
    cal["Festival_Name"] = None

    for d, n in cal.loc[cal["Holiday"] == 1, ["Date", "Holiday_Name"]].itertuples(
        index=False
    ):
        if any(f in str(n) for f in MAJOR_FESTIVALS):
            mask = (cal["Date"] > d - pd.Timedelta(days=window)) & (cal["Date"] <= d)
            cal.loc[mask, "Festival_Window"] = 1
            cal.loc[mask, "Festival_Name"] = n

    cal["Festival_Window"] = cal["Festival_Window"].astype("int8")
    logger.info(
        "Built holiday calendar with %d days (%d holidays, %d festival window days).",
        len(cal),
        cal["Holiday"].sum(),
        cal["Festival_Window"].sum(),
    )
    return cal
