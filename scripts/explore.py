import pandas as pd

df = pd.read_csv("data/raw/dataset.csv")
print(df.shape)
print(df.columns.tolist()[:5])
print("diseases:", df["Disease"].nunique())
print(df.iloc[0].tolist())

sev = pd.read_csv("data/raw/Symptom-severity.csv")
print(sev.head())