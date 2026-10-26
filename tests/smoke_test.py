"""Dependency-light smoke tests for core CSV cleaning behavior."""
from io import StringIO
import pandas as pd

sample = pd.read_csv(StringIO("name,amount,region\n Alice ,10,North\nBob,,South\nBob,,South\n"))
original = sample.copy(deep=True)

# Duplicate detection/removal
assert int(sample.duplicated().sum()) == 1
without_duplicates = sample.drop_duplicates().reset_index(drop=True)
assert len(without_duplicates) == 2

# Whitespace trim leaves missing values untouched
trimmed = original.copy()
for col in trimmed.select_dtypes(include=["object", "string"]).columns:
    trimmed[col] = trimmed[col].map(lambda value: value.strip() if isinstance(value, str) else value)
assert trimmed.loc[0, "name"] == "Alice"
assert pd.isna(trimmed.loc[1, "amount"])

# Fill numeric missing value with median
filled = original.copy()
filled["amount"] = filled["amount"].fillna(filled["amount"].median())
assert filled["amount"].isna().sum() == 0
assert filled.loc[1, "amount"] == 10

# Original remains unchanged
assert original.loc[0, "name"] == " Alice "
assert original["amount"].isna().sum() == 2
print("PASS: duplicate removal, whitespace trimming, numeric missing-value fill, and original-copy preservation")
