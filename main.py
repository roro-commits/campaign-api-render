"""Skin clinic campaign analysis API — response rate (%) by customer segment."""
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

DATA = Path(__file__).parent / "skin_clinic_campaign.csv"

# segment name -> (source column, category order)
SEGMENTS = {
    "Gender": ("Gender", ["Female", "Male"]),
    "Age Group": ("AgeGroup", ["<30", "30-50", ">50"]),
    "Purchase Last Quarter": ("Purchase_Last_Quarter", ["Yes", "No"]),
    "Product Usage": ("ProductUsage", ["1-4", "5-8", ">8"]),
}

app = FastAPI(title="Skin Clinic Campaign Analysis")


def load() -> pd.DataFrame:
    """Read the CSV on every call so a redeployed file shows up on Excel refresh."""
    df = pd.read_csv(DATA)
    df["ProductUsage"] = pd.cut(
        df["Unique_Products_Purchased"], bins=[0, 4, 8, float("inf")], labels=["1-4", "5-8", ">8"]
    ).astype(str)
    df["Responded"] = df["Response_to_Campaign"].eq("Yes")
    return df


def response_rate(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    """One row per category: customers, responders, response rate (%)."""
    col, order = SEGMENTS[segment]
    out = (
        df.groupby(col)["Responded"]
        .agg(Customers="size", Responders="sum")
        .reindex(order)
        .rename_axis("Category")
        .reset_index()
    )
    out["ResponseRatePct"] = (100 * out["Responders"] / out["Customers"]).round(2)
    out.insert(0, "Segment", segment)
    return out


@app.get("/")
def root():
    return {"endpoint": "/campaign-analysis", "docs": "/docs", "segments": list(SEGMENTS)}


@app.get("/campaign-analysis")
def campaign_analysis(segment: str | None = None, format: str = "json"):
    """All four tables stacked (filter with ?segment=Gender). ?format=csv for CSV."""
    if segment and segment not in SEGMENTS:
        raise HTTPException(404, f"segment must be one of {list(SEGMENTS)}")
    df = load()
    table = pd.concat([response_rate(df, s) for s in ([segment] if segment else SEGMENTS)], ignore_index=True)
    if format == "csv":
        return PlainTextResponse(table.to_csv(index=False), media_type="text/csv")
    return table.to_dict(orient="records")
