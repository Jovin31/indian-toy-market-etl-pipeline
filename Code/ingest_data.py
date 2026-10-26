import pandas as pd
import os
from sqlalchemy import create_engine

print("Running Ingestion Task")

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "indian_toy_market_sales_data.csv")
df = pd.read_csv(file_path)

print(f"Successfully read {len(df)} rows from CSV.")

engine = create_engine("mysql+pymysql://root:@host.docker.internal:3306/indian_toy_market_raw")

print("Loading data into 'indian_toy_market_raw' database...")
df.to_sql(
    name="indian_toy_market_sales", 
    con=engine, 
    if_exists="replace", 
    index=False
)

print("Ingestion Task Success")