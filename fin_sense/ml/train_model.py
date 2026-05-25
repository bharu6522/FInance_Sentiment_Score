import pandas as pd
import numpy as np 
import os 
import sqlite3
import pickle
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb 
import shap 
from feature_builder import build_feature_matrix
from sklearn.utils.class_weight import compute_sample_weight

load_dotenv()
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finsense.db"))
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "model.pkl"))


FEATURES = [
    "return_1d",
    "return_2d",
    "return_3d",
    "volatility_5d",
    "avg_return_5d",

    "volume_change",
    "avg_sentiment",
    "max_sentiment",
    "min_sentiment",

    "sentiment_momentum",
    "positive_count",
    "negative_count",
    "high_impact_count",
    "article_count"
]


def train():

    df = build_feature_matrix()
    df = df.dropna(subset= FEATURES)

    X = df[FEATURES]
    y = df["target"]

    X = X.replace([np.inf, -np.inf], np.nan)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset= FEATURES)

    print(f"\n[train] Total usable rows : {len(df)}")
    print(f"[train] Target distribution:\n{df['target'].value_counts()}")

    le= LabelEncoder()
    y_encoded = le.fit_transform(y)

    print(f"\n[train] Label encoding: {dict(zip(le.classes_, le.transform(le.classes_)))}")

    X_train, X_test, y_train, y_test = train_test_split(X,y_encoded, test_size=0.2,random_state=42, shuffle= False)
    print(f"[train] Train size: {len(X_train)}  Test size: {len(X_test)}")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        # use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        scale_pos_weight = 1
    )

    sample_weights = compute_sample_weight(class_weight='balanced', y= y_train)

    model.fit(
        X_train, y_train,
        sample_weight = sample_weights,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    y_pred = model.predict(X_test)
    print("\n[train] Classification Report:")
    print(classification_report(y_test, y_pred, target_names= le.classes_))

    print("[train] Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    print("\n[train] Computing SHAP values...")
    
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)

        shap_importance = pd.DataFrame({
            "feature":    FEATURES,
            "importance": np.abs(shap_values).mean(axis=(0, 2))
                        if len(np.array(shap_values).shape) == 3
                        else np.abs(shap_values).mean(axis=0)
        })

        print("\n[train] Top features by SHAP:")
        print(shap_importance.to_string(index=False))
    
    except Exception as e:

        print(f"[train] SHAP failed ({e}) — falling back to XGBoost feature importance")
        explainer = None

        importance = pd.DataFrame({
        "feature":    FEATURES,
        "importance": model.feature_importances_ }).sort_values("importance", ascending=False)

        print("\n[train] Top features by importance:")
        print(importance.to_string(index=False))

        
    os.makedirs("models", exist_ok=True)
    bundle = {
        "model":      model,
        "encoder":    le,
        "features":   FEATURES,
        "explainer":  explainer,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)

    print(f"\n[train] Model saved to {MODEL_PATH}")
    return bundle


if __name__ == "__main__":
    train()
    
