# %%
from pathlib import Path

import pandas as pd
from dateutil import parser
from sqlalchemy import create_engine


# ============================================================
# CONFIGURATION
# ============================================================

# "csv"  = validate using the local CSV
# "mysql" = read from the MySQL raw database
SOURCE_MODE = "csv"

# Keep True until all validation results are reviewed.
DRY_RUN = True

RAW_DATABASE_URL = (
    "mysql+pymysql://root:@host.docker.internal:3306/"
    "indian_toy_market_raw"
)

FINAL_DATABASE_URL = (
    "mysql+pymysql://root:@host.docker.internal:3306/"
    "indian_toy_market_final"
)

CSV_PATH = (
    Path(__file__).resolve().parent
    / "indian_toy_market_sales_data.csv"
)


# ============================================================
# LOAD SOURCE DATA
# ============================================================

print("Running Transformation Task")

if SOURCE_MODE == "csv":
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            "Source CSV not found: {}".format(CSV_PATH)
        )

    df = pd.read_csv(CSV_PATH)
    print("Source: local CSV")

elif SOURCE_MODE == "mysql":
    engine_raw = create_engine(RAW_DATABASE_URL)

    try:
        df = pd.read_sql(
            "SELECT * FROM indian_toy_market_sales",
            con=engine_raw
        )
    finally:
        engine_raw.dispose()

    print("Source: MySQL raw database")

else:
    raise ValueError(
        "SOURCE_MODE must be either 'csv' or 'mysql'."
    )

print("Rows loaded: {:,}".format(len(df)))
print("Columns loaded: {}".format(len(df.columns)))

if df.empty:
    raise ValueError("The source dataset is empty.")

required_columns = [
    "Transaction_ID",
    "Transaction_Date",
    "Brand",
    "Product_ID",
    "Region",
    "City",
    "City_Tier",
    "Sales_Channel",
    "Customer_Type",
    "Target_Age_Group",
    "Quantity",
    "Unit_Price_INR",
    "Gross_Revenue_INR",
    "Discount_Amount_INR",
    "Net_Revenue_INR",
    "Customer_Rating",
    "Safety_Certified",
    "Returned",
    "Brand_Type",
    "Product_Category",
    "Product_Subcategory",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        "Missing required columns: {}".format(
            ", ".join(missing_columns)
        )
    )


# ============================================================
# CLEAN REGION
# ============================================================

city_region_counts = (
    df.dropna(subset=["City", "Region"])
      .groupby("City")["Region"]
      .nunique()
)

conflicting_cities = city_region_counts[
    city_region_counts > 1
]

if not conflicting_cities.empty:
    raise ValueError(
        "Some cities map to multiple regions. "
        "Region imputation needs review: {}".format(
            ", ".join(
                conflicting_cities.index.astype(str).tolist()[:10]
            )
        )
    )

region_map = (
    df.dropna(subset=["City", "Region"])
      .drop_duplicates(subset=["City"])
      .set_index("City")["Region"]
      .to_dict()
)

missing_region_before = int(df["Region"].isna().sum())

df["Region"] = df["Region"].fillna(
    df["City"].map(region_map)
)

print(
    "Region values filled: {}".format(
        missing_region_before
        - int(df["Region"].isna().sum())
    )
)

print(
    "Region values still missing: {}".format(
        int(df["Region"].isna().sum())
    )
)


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

# Existing project convention: -1 represents a missing rating.
df["Customer_Rating"] = df["Customer_Rating"].fillna(-1)


# Safety_Certified
mapping_safety = {
    "yes": "Yes",
    "Yes": "Yes",
    "TRUE": "Yes",
    "Y": "Yes",
    "no": "No",
    "No": "No",
    "FALSE": "No",
    "N": "No",
}

df["Safety_Certified"] = (
    df["Safety_Certified"].replace(mapping_safety)
)

# Existing project assumption:
# missing certification values are represented as "No".
df["Safety_Certified"] = (
    df["Safety_Certified"].fillna("No")
)


# Returned
mapping_returned = {
    "no": "No",
    "No": "No",
    "N": "No",
    "Y": "Yes",
    "yes": "Yes",
    "Yes": "Yes",
}

df["Returned"] = df["Returned"].replace(mapping_returned)

# Existing project assumption:
# missing return statuses are represented as "No".
df["Returned"] = df["Returned"].fillna("No")


# Customer_Type
df["Customer_Type"] = (
    df["Customer_Type"].fillna("Unknown")
)


# ============================================================
# STANDARDIZE CATEGORICAL VALUES
# ============================================================

# Brand
df["Brand"] = df["Brand"].str.strip().str.title()

mapping_brand = {
    "Toyzone": "Toy Zone",
    "Fisher-Price": "Fisher Price",
    "Okplay": "OK Play",
    "Ok Play": "OK Play",
    "Funskool India": "Funskool",
    "Hotwheels": "Hot Wheels",
}

df["Brand"] = df["Brand"].replace(mapping_brand)

print(
    "Unique brands after standardization: {}".format(
        df["Brand"].nunique(dropna=True)
    )
)


# City
df["City"] = df["City"].str.strip().str.title()


# Sales channel
df["Sales_Channel"] = (
    df["Sales_Channel"].str.strip().str.title()
)

mapping_channel = {
    "Amazon.In": "Amazon",
    "Hamleys Store": "Hamleys",
    "Website": "Brand Website",
}

df["Sales_Channel"] = (
    df["Sales_Channel"].replace(mapping_channel)
)

print(
    "Unique sales channels after standardization: {}".format(
        df["Sales_Channel"].nunique(dropna=True)
    )
)


# Target age group
df["Target_Age_Group"] = (
    df["Target_Age_Group"]
      .str.replace(" years", "", case=False, regex=False)
)


# ============================================================
# NORMALIZE NUMERIC VALUES
# ============================================================

df["Quantity"] = pd.to_numeric(
    df["Quantity"], errors="coerce"
)

df["Unit_Price_INR"] = pd.to_numeric(
    df["Unit_Price_INR"], errors="coerce"
)

df["Gross_Revenue_INR"] = pd.to_numeric(
    df["Gross_Revenue_INR"], errors="coerce"
)

df["Discount_Amount_INR"] = pd.to_numeric(
    df["Discount_Amount_INR"], errors="coerce"
)

df["Net_Revenue_INR"] = pd.to_numeric(
    df["Net_Revenue_INR"], errors="coerce"
)


# Normalize negative quantities in the transformed data.
negative_quantity_count = int(
    (df["Quantity"] < 0).sum()
)

df["Quantity"] = df["Quantity"].abs()


# Normalize price signs, but do not automatically divide by 10.
negative_price_count = int(
    (df["Unit_Price_INR"] < 0).sum()
)

df["Unit_Price_INR"] = df["Unit_Price_INR"].abs()

print(
    "Negative quantities normalized: {}".format(
        negative_quantity_count
    )
)

print(
    "Negative unit prices normalized by sign: {}".format(
        negative_price_count
    )
)


# ============================================================
# FINANCIAL DATA QUALITY CHECKS
# ============================================================

gross_reference = df["Gross_Revenue_INR"].abs()

expected_gross = (
    df["Unit_Price_INR"] * df["Quantity"]
)

gross_difference = (
    expected_gross - gross_reference
).abs()

gross_mismatch_count = int(
    (gross_difference > 1).sum()
)


# Detect the previously observed 10x pattern.
# This is a flag only; no revenue or price is changed here.
ratio = expected_gross.div(
    gross_reference.where(gross_reference.ne(0))
)

factor_10_mask = (
    ratio.notna()
    & ((ratio - 10).abs() < 1e-6)
)

factor_10_count = int(factor_10_mask.sum())


# Validate gross revenue less discount against net revenue.
discount_reference = df["Discount_Amount_INR"]
net_reference = df["Net_Revenue_INR"]

net_difference = (
    gross_reference
    - discount_reference
    - net_reference
).abs()

net_mismatch_count = int(
    (net_difference > 1).sum()
)

print("\n=== FINANCIAL DATA QUALITY ===")

print(
    "Gross-revenue mismatches above INR 1: {}".format(
        gross_mismatch_count
    )
)

print(
    "Rows matching the 10x pattern: {}".format(
        factor_10_count
    )
)

print(
    "Net-revenue mismatches above INR 1: {}".format(
        net_mismatch_count
    )
)

if gross_mismatch_count:
    print(
        "WARNING: Unit price x quantity does not match gross "
        "revenue in some rows. Existing revenue values retained."
    )

if net_mismatch_count:
    print(
        "WARNING: Gross revenue minus discount does not match "
        "net revenue in some rows."
    )


# ============================================================
# PARSE TRANSACTION DATES
# ============================================================

def smart_date_parser(date_value):
    if pd.isna(date_value):
        return pd.NaT

    try:
        if not isinstance(date_value, str):
            return date_value

        return parser.parse(date_value)

    except (ValueError, TypeError, OverflowError):
        return pd.NaT


df["Transaction_Date"] = (
    df["Transaction_Date"].apply(smart_date_parser)
)

df["Transaction_Date"] = pd.to_datetime(
    df["Transaction_Date"],
    errors="coerce"
)

invalid_date_count = int(
    df["Transaction_Date"].isna().sum()
)

print("Invalid transaction dates: {}".format(invalid_date_count))

if invalid_date_count:
    raise ValueError(
        "Some transaction dates could not be parsed. "
        "Review the dataset before continuing."
    )


# ============================================================
# BUILD PRODUCT DIMENSION
# ============================================================

product_columns = [
    "Product_ID",
    "Brand",
    "Brand_Type",
    "Product_Category",
    "Product_Subcategory",
]

# The source contains Product_ID values with inconsistent
# attributes. Preserve each distinct normalized profile rather
# than silently discarding rows based only on Product_ID.
dim_product = (
    df[product_columns]
    .drop_duplicates()
    .reset_index(drop=True)
)

# Each distinct product profile receives a surrogate key.
dim_product["Product_Key"] = (
    "PROD_" + (dim_product.index + 1).astype(str)
)

print(
    "Distinct product profiles: {}".format(len(dim_product))
)


# ============================================================
# BUILD LOCATION DIMENSION
# ============================================================

dim_location = (
    df[["Region", "City", "City_Tier"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

dim_location["Location_ID"] = (
    "LOC_" + (dim_location.index + 1).astype(str)
)


# ============================================================
# BUILD CUSTOMER DIMENSION
# ============================================================

customer_columns = [
    "Customer_Type",
    "Target_Age_Group",
    "Sales_Channel",
]

dim_customer_channel = (
    df[customer_columns]
    .drop_duplicates()
    .reset_index(drop=True)
)

dim_customer_channel["Customer_ID"] = (
    "CC_" + (dim_customer_channel.index + 1).astype(str)
)


# ============================================================
# BUILD DATE DIMENSION
# ============================================================

dim_date = pd.DataFrame(
    {"Transaction_Date": df["Transaction_Date"].unique()}
)

dim_date = (
    dim_date.sort_values("Transaction_Date")
    .reset_index(drop=True)
)

dim_date["Date_Key"] = (
    dim_date["Transaction_Date"].dt.strftime("%Y%m%d").astype(int)
)

dim_date["Year"] = dim_date["Transaction_Date"].dt.year
dim_date["Month"] = dim_date["Transaction_Date"].dt.month

dim_date["Month_Name"] = (
    dim_date["Transaction_Date"].dt.strftime("%B")
)

dim_date["Quarter"] = (
    "Q" + dim_date["Transaction_Date"].dt.quarter.astype(str)
)

dim_date["Day_of_Week"] = (
    dim_date["Transaction_Date"].dt.strftime("%A")
)


# ============================================================
# BUILD FACT TABLE
# ============================================================

fact_sales = pd.merge(
    df,
    dim_location,
    on=["Region", "City", "City_Tier"],
    how="left",
    validate="many_to_one"
)

fact_sales = pd.merge(
    fact_sales,
    dim_customer_channel,
    on=customer_columns,
    how="left",
    validate="many_to_one"
)

# Add Product_Key using the full normalized product profile.
fact_sales = pd.merge(
    fact_sales,
    dim_product,
    on=product_columns,
    how="left",
    validate="many_to_one"
)

fact_sales["Date_Key"] = (
    fact_sales["Transaction_Date"]
    .dt.strftime("%Y%m%d")
    .astype(int)
)

fact_sales = fact_sales[
    [
        "Transaction_ID",
        "Date_Key",
        "Product_Key",
        "Product_ID",
        "Location_ID",
        "Customer_ID",
        "Quantity",
        "Unit_Price_INR",
        "Gross_Revenue_INR",
        "Discount_Amount_INR",
        "Net_Revenue_INR",
        "Customer_Rating",
        "Returned",
    ]
]


# ============================================================
# VALIDATE STAR SCHEMA
# ============================================================

tables_to_upload = {
    "dim_product": dim_product,
    "dim_location": dim_location,
    "dim_customer": dim_customer_channel,
    "dim_date": dim_date,
    "fact_sales": fact_sales,
}

print("\n=== STAR SCHEMA SUMMARY ===")

for table_name, dataframe in tables_to_upload.items():
    print(
        "{}: {:,} rows".format(table_name, len(dataframe))
    )

product_key_missing = int(
    fact_sales["Product_Key"].isna().sum()
)

location_key_missing = int(
    fact_sales["Location_ID"].isna().sum()
)

customer_key_missing = int(
    fact_sales["Customer_ID"].isna().sum()
)

print("\n=== KEY VALIDATION ===")
print("Fact rows without Product_Key:", product_key_missing)
print("Fact rows without Location_ID:", location_key_missing)
print("Fact rows without Customer_ID:", customer_key_missing)

if len(fact_sales) != len(df):
    raise ValueError(
        "Fact row count differs from source row count. "
        "Review dimension joins before continuing."
    )

if (
    product_key_missing
    or location_key_missing
    or customer_key_missing
):
    raise ValueError(
        "Some fact rows do not map to a dimension key."
    )


# ============================================================
# DRY RUN
# ============================================================

print("\n=== DRY-RUN SUMMARY ===")
print("Rows processed: {:,}".format(len(df)))
print("Invalid dates: {}".format(invalid_date_count))
print("Negative quantities normalized: {}".format(
    negative_quantity_count
))
print("Negative prices normalized by sign: {}".format(
    negative_price_count
))
print("Rows matching 10x pattern: {}".format(factor_10_count))
print("Gross-revenue mismatches: {}".format(
    gross_mismatch_count
))
print("Net-revenue mismatches: {}".format(
    net_mismatch_count
))

if DRY_RUN:
    print("\nDry run complete. No data was written to MySQL.")
    raise SystemExit(0)


# ============================================================
# LOAD TO MYSQL FINAL
# ============================================================
# Only reached after DRY_RUN is explicitly set to False.
# if_exists="replace" replaces existing destination tables.

if SOURCE_MODE != "mysql":
    raise RuntimeError(
        "Database loading requires SOURCE_MODE = 'mysql'."
    )

engine_final = create_engine(FINAL_DATABASE_URL)

try:
    for table_name, dataframe in tables_to_upload.items():
        load_options = {
            "name": table_name,
            "con": engine_final,
            "if_exists": "replace",
            "index": False,
        }

        if table_name == "fact_sales":
            load_options["chunksize"] = 10000

        dataframe.to_sql(**load_options)

        print(
            "Table '{}' uploaded successfully ({:,} rows).".format(
                table_name, len(dataframe)
            )
        )
finally:
    engine_final.dispose()

print("\nAll star-schema tables uploaded successfully.")