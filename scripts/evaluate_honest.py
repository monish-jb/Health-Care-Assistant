import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

df = pd.read_csv("data/processed/symptoms.csv").drop_duplicates()
print("unique rows:", len(df))

X, y = df.drop(columns=["condition"]), df["condition"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
clf = RandomForestClassifier(n_estimators=300, random_state=42).fit(Xtr, ytr)


def top_k_accuracy(model, Xs, ys, k):
    """Is the true disease among the model's k best guesses?"""
    proba = model.predict_proba(Xs)
    best = np.argsort(proba, axis=1)[:, -k:]
    return float(np.mean([truth in model.classes_[row] for truth, row in zip(ys, best)]))



print("all symptoms   top-1:", round(top_k_accuracy(clf, Xte, yte, 1), 3))
print("all symptoms   top-3:", round(top_k_accuracy(clf, Xte, yte, 3), 3))


rng = np.random.default_rng(42)
values = Xte.values.copy()
for i in range(len(values)):
    present = np.flatnonzero(values[i])
    if len(present) > 2:
        drop = rng.choice(present, size=len(present) // 2, replace=False)
        values[i, drop] = 0
Xhalf = pd.DataFrame(values, columns=Xte.columns)

print("half symptoms  top-1:", round(top_k_accuracy(clf, Xhalf, yte, 1), 3))
print("half symptoms  top-3:", round(top_k_accuracy(clf, Xhalf, yte, 3), 3))