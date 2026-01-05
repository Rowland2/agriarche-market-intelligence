# data_model.py
"""
Prepare data, train a RandomForest regression model and save artifacts.
This script automatically finds a file with base name:
    "Predictive Analysis Commodity pricing"
It will try .xlsx, .xls, .csv extensions.
"""

import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_NAME = "Predictive Analysis Commodity pricing"
SEARCH_EXTS = [".xlsx", ".xls", ".csv"]
OUT_DIR = "commodity_model"
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------
# FIND DATA FILE
# ---------------------------------------------------------
def find_data_file():
    for ext in SEARCH_EXTS:
        candidate = BASE_NAME + ext
        if os.path.exists(candidate):
            return candidate

    # fallback: case insensitive search
    for f in os.listdir("."):
        if f.lower().startswith(BASE_NAME.lower()):
            return f

    raise FileNotFoundError(
        f"Could not find file starting with '{BASE_NAME}' in current folder."
    )


# ---------------------------------------------------------
# AUTO-DETECT COLUMNS
# ---------------------------------------------------------
def detect_columns(df):
    cols = df.columns.tolist()

    # 1. detect date
    date_col = None
    for c in cols:
        if "date" in c.lower() or "timestamp" in c.lower():
            date_col = c
            break

    if date_col is None:
        for c in cols:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                date_col = c
                break

    if date_col is None:
        for c in cols:
            if pd.to_datetime(df[c], errors="coerce").notna().sum() > 0:
                date_col = c
                break

    # 2. detect price
    price_col = None
    for c in cols:
        if any(k in c.lower() for k in ("price", "amount", "cost", "bag", "kg")):
            price_col = c
            break

    if price_col is None:
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        price_col = numeric_cols[0] if numeric_cols else None

    # 3. detect commodity
    commodity_col = None
    for c in cols:
        if any(k in c.lower() for k in ("commodity", "product", "market", "buyer")):
            commodity_col = c
            break

    return date_col, price_col, commodity_col


# ---------------------------------------------------------
# PREPARE DATA
# ---------------------------------------------------------
def prepare(df, date_col, price_col, commodity_col):
    df = df.copy()

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)

    df = df.rename(columns={date_col: "ds", price_col: "price"})

    # Assign commodity column
    if commodity_col is None or commodity_col not in df.columns:
        df["commodity"] = "ALL"
    else:
        df["commodity"] = df[commodity_col].astype(str).fillna("NA")

    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Time features
    df["dayofweek"] = df["ds"].dt.dayofweek
    df["month"] = df["ds"].dt.month

    # Rolling + lag features per commodity
    def create_lags(g):
        g = g.sort_values("ds").copy()
        g["lag_1"] = g["price"].shift(1)
        g["lag_7"] = g["price"].shift(7)
        g["ma_7"] = g["price"].rolling(7, min_periods=1).mean()
        g["ma_30"] = g["price"].rolling(30, min_periods=1).mean()
        return g

    df = df.groupby("commodity", dropna=False).apply(create_lags).reset_index(drop=True)

    # Simple signal (BUY / DON'T BUY)
    df["signal"] = np.where(df["price"] < df["ma_30"], "DON'T BUY", "BUY")

    return df


# ---------------------------------------------------------
# TRAIN MODEL AND SAVE
# ---------------------------------------------------------
def train_and_save(df):
    df_model = df.dropna(subset=["lag_1"]).copy()
    df_model = df_model[df_model["price"].notna()]

    if df_model.empty:
        raise RuntimeError(
            "Not enough data to train after creating lag features. Add more rows!"
        )

    # Encode commodity
    le = LabelEncoder()
    df_model["commodity_le"] = le.fit_transform(df_model["commodity"])

    feature_cols = [
        "lag_1",
        "lag_7",
        "ma_7",
        "ma_30",
        "dayofweek",
        "month",
        "commodity_le",
    ]

    X = df_model[feature_cols].ffill().fillna(0)
    y = df_model["price"]

    # Train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Train model
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5  # sqrt(mse) because old sklearn doesn't support squared=False

    # Save artifacts
    joblib.dump(model, os.path.join(OUT_DIR, "rf_model.joblib"))
    joblib.dump(le, os.path.join(OUT_DIR, "label_encoder.joblib"))

    # Save sample of processed data
    df_model.to_csv(os.path.join(OUT_DIR, "training_sample_with_signals.csv"), index=False)

    # Report
    report = {
        "rows_processed": int(len(df)),
        "unique_commodities": int(df["commodity"].nunique()),
        "mae": float(mae),
        "rmse": float(rmse),
    }

    # Save report.json
    import json

    with open(os.path.join(OUT_DIR, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\n✅ Model training complete!")
    print("Saved model & artifacts →", OUT_DIR)
    print("MAE:", mae)
    print("RMSE:", rmse)

    return model, le, report


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    data_file = find_data_file()
    print("Using data file:", data_file)

    # Load file
    if data_file.lower().endswith(".csv"):
        df = pd.read_csv(data_file)
    else:
        df = pd.read_excel(data_file)

    date_col, price_col, commodity_col = detect_columns(df)

    print("Detected → date:", date_col, "| price:", price_col, "| commodity:", commodity_col)

    df_prepared = prepare(df, date_col, price_col, commodity_col)

    model, le, report = train_and_save(df_prepared)

    print("\nFinal Report:")
    print(report)


if __name__ == "__main__":
    main()

