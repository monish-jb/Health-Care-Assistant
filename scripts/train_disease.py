"""Train the symptom->condition model. CSV: one row per case, columns = symptoms (0/1) + 'condition'.
Usage: python scripts/train_disease.py --csv data/raw/symptoms.csv"""
import argparse

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

p = argparse.ArgumentParser()
p.add_argument("--csv", required=True)
p.add_argument("--out", default="app/disease/model.pkl")
a = p.parse_args()

df = pd.read_csv(a.csv)
X, y = df.drop(columns=["condition"]), df["condition"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
clf = RandomForestClassifier(n_estimators=300, random_state=42).fit(Xtr, ytr)
print(classification_report(yte, clf.predict(Xte)))
joblib.dump({"model": clf, "symptoms": list(X.columns)}, a.out)
