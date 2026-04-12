import pandas as pd
from sqlalchemy import create_engine

# STEP 1: Load CSV
df = pd.read_csv("data/ubereats_sales.csv")

# STEP 2: Clean column names
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# STEP 3: Preview data
print("Columns:", df.columns)
print(df.head())

# STEP 4: Create SQLite database
engine = create_engine("sqlite:///orders.db")

# STEP 5: Store data into table
df.to_sql("orders", engine, if_exists="replace", index=False)

print("Database created successfully!")