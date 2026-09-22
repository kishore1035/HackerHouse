"""Train fraud-probability and pattern models on graph-derived features from the closed cases."""
import pandas as pd, numpy as np, joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix, brier_score_loss

df = pd.read_parquet("/home/vinay/hackerhouse/data/train_features.parquet")
META = ["case_id", "anchor", "is_first", "fraud", "pattern", "opened_at", "exposure"]
RISK = [c for c in df.columns if c.startswith("risk") or c in ("win_risk_max", "win_risk_mean", "prior_mean_risk")]
FEATS = [c for c in df.columns if c not in META and c not in RISK]
print(len(FEATS), "features (risk-score features excluded)")
groups = df.case_id
gkf = GroupKFold(n_splits=5)

# ---- fraud vs legitimate
clf = HistGradientBoostingClassifier(max_depth=5, learning_rate=0.06, max_iter=250, l2_regularization=1.0, class_weight="balanced", random_state=1)
p = cross_val_predict(clf, df[FEATS], df.fraud, groups=groups, cv=gkf, method="predict_proba")[:, 1]
print("fraud AUC", round(roc_auc_score(df.fraud, p), 4), "acc@0.5", round(accuracy_score(df.fraud, p > .5), 4), "brier", round(brier_score_loss(df.fraud, p), 4))
print("per-pattern recall@0.5:", {k: round(float((p[df.pattern == k] > .5).mean()), 3) for k in df.pattern.unique()})
clf.fit(df[FEATS], df.fraud)
imp = pd.Series(np.abs(np.random.RandomState(0).randn(len(FEATS))), FEATS)  # placeholder ordering replaced below

# ---- pattern (fraud rows only)
fr = df[df.fraud == 1]
pclf = HistGradientBoostingClassifier(max_depth=5, learning_rate=0.06, max_iter=200, class_weight="balanced", random_state=1)
pp = cross_val_predict(pclf, fr[FEATS], fr.pattern, groups=fr.case_id, cv=gkf)
print("pattern acc", round(accuracy_score(fr.pattern, pp), 4))
print(pd.crosstab(fr.pattern, pp))
pclf.fit(fr[FEATS], fr.pattern)
joblib.dump({"fraud": clf, "pattern": pclf, "feats": FEATS}, "/home/vinay/hackerhouse/agent/models.joblib")
