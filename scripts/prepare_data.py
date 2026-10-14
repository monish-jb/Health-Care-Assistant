import pandas as pd

# 1. Load the original dataset
df = pd.read_csv("data/raw/dataset.csv")
symptom_cols = [c for c in df.columns if c.startswith("Symptom_")]


# 2. Clean a symptom name: " skin_rash" -> "skin_rash", " dischromic _patches" -> "dischromic_patches"
def clean(s):
    return s.strip().lower().replace(" ", "_")


# 3. Collect every different symptom in the whole dataset
all_symptoms = set()
for col in symptom_cols:
    for value in df[col]:
        if pd.notna(value):              # skip the empty (nan) cells
            all_symptoms.add(clean(value))
all_symptoms = sorted(all_symptoms)


# 4. Build one row per patient: 1 if they have the symptom, else 0
rows = []
for _, row in df.iterrows():
    has = {clean(row[c]) for c in symptom_cols if pd.notna(row[c])}
    new_row = {s: (1 if s in has else 0) for s in all_symptoms}
    new_row["condition"] = row["Disease"].strip()
    rows.append(new_row)

out = pd.DataFrame(rows)


# 5. Save it
out.to_csv("data/processed/symptoms.csv", index=False)
print("shape:", out.shape)
print("unique rows:", out.drop_duplicates().shape[0])