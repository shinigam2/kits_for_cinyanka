"""Модуль обучения и валидации моделей машинного обучения для прогнозирования эвтрофикации.

Реализует две модельные задачи:
1. Регрессия: Прогноз численной концентрации Chl-a (мкг/л) через 10 дней.
   - Baseline 1: Наивный прогноз y(t+1) = y(t)
   - Baseline 2: Ridge / Линейная регрессия
   - Main: LightGBM Regressor
2. Классификация: Оценка вероятности наступления цветения водоема (Chl-a >= 25 мкг/л).
   - Baseline: Logistic Regression
   - Main: LightGBM Classifier

Валидация:
- Строго временное разбиение (Time-based Out-Of-Time Split):
  * Обучающая выборка (Train): 2020-01-01 - 2023-12-31 (4 года)
  * Тестовая выборка (Test):  2024-01-01 - 2025-12-31 (2 года)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "month",
    "day_of_year",
    "sin_doy",
    "cos_doy",
    "mean_depth_m",
    "surface_area_km2",
    "is_reservoir",
    "chl_a_current",
    "chl_a_lag10d",
    "chl_a_growth_10d",
    "turbidity_current",
    "tsi_current",
    "temp_mean_7d",
    "temp_max_7d",
    "temp_mean_14d",
    "temp_mean_21d",
    "hot_days_14d",
    "precip_sum_7d",
    "precip_sum_14d",
    "radiation_mean_7d",
    "calm_fraction_7d",
    "wind_mean_7d",
]


def load_and_split_data(
    data_path: Path, split_date: str = "2024-01-01"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(data_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    train_df = df[df["date"] < split_date].copy()
    test_df = df[df["date"] >= split_date].copy()

    logger.info(
        f"Данные разделены: Обучение {len(train_df)} записей (до {split_date}), "
        f"Тест {len(test_df)} записей (с {split_date})"
    )
    return train_df, test_df


def train_regression_models(
    train_df: pd.DataFrame, test_df: pd.DataFrame, models_dir: Path
) -> Dict[str, Any]:
    """Обучение и сравнение регрессионных моделей для хлорофилла-a."""
    X_train, y_train = train_df[FEATURE_COLS], train_df["target_chl_a_next_10d"]
    X_test, y_test = test_df[FEATURE_COLS], test_df["target_chl_a_next_10d"]

    # 1. Наивный бейзлайн (y_pred = chl_a_current)
    naive_pred = test_df["chl_a_current"]
    naive_rmse = float(np.sqrt(mean_squared_error(y_test, naive_pred)))
    naive_mae = float(mean_absolute_error(y_test, naive_pred))
    naive_r2 = float(r2_score(y_test, naive_pred))

    # 2. Линейная регрессия (Ridge)
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    ridge_pred = ridge.predict(X_test)
    ridge_rmse = float(np.sqrt(mean_squared_error(y_test, ridge_pred)))
    ridge_mae = float(mean_absolute_error(y_test, ridge_pred))
    ridge_r2 = float(r2_score(y_test, ridge_pred))

    # 3. LightGBM Regressor
    lgb_reg = lgb.LGBMRegressor(
        n_estimators=120,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=18,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbose=-1,
    )
    lgb_reg.fit(X_train, y_train)
    lgb_pred = lgb_reg.predict(X_test)
    lgb_rmse = float(np.sqrt(mean_squared_error(y_test, lgb_pred)))
    lgb_mae = float(mean_absolute_error(y_test, lgb_pred))
    lgb_r2 = float(r2_score(y_test, lgb_pred))

    # Важность признаков
    importance = dict(zip(FEATURE_COLS, [float(x) for x in lgb_reg.feature_importances_]))
    sorted_importance = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True))

    joblib.dump(lgb_reg, models_dir / "lgb_regressor_chla.joblib")
    joblib.dump(ridge, models_dir / "ridge_regressor_chla.joblib")

    results = {
        "naive_baseline": {"rmse": naive_rmse, "mae": naive_mae, "r2": naive_r2},
        "ridge_regression": {"rmse": ridge_rmse, "mae": ridge_mae, "r2": ridge_r2},
        "lightgbm_regressor": {"rmse": lgb_rmse, "mae": lgb_mae, "r2": lgb_r2},
        "top_features_importance": dict(list(sorted_importance.items())[:8]),
    }
    logger.info(f"Результаты регрессии Chl-a (Test Set): LightGBM R²={lgb_r2:.3f}, RMSE={lgb_rmse:.2f} мкг/л")
    return results


def train_classification_models(
    train_df: pd.DataFrame, test_df: pd.DataFrame, models_dir: Path
) -> Dict[str, Any]:
    """Обучение и сравнение классификаторов риска цветения (Bloom Risk)."""
    X_train, y_train = train_df[FEATURE_COLS], train_df["target_bloom_risk_next_10d"]
    X_test, y_test = test_df[FEATURE_COLS], test_df["target_bloom_risk_next_10d"]

    # 1. Логистическая регрессия (Baseline)
    log_reg = LogisticRegression(max_iter=1000, random_state=42)
    log_reg.fit(X_train, y_train)
    log_pred = log_reg.predict(X_test)
    log_prob = log_reg.predict_proba(X_test)[:, 1]

    # 2. LightGBM Classifier
    lgb_clf = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        num_leaves=12,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    lgb_clf.fit(X_train, y_train)
    lgb_pred = lgb_clf.predict(X_test)
    lgb_prob = lgb_clf.predict_proba(X_test)[:, 1]

    def eval_clf(y_true, y_pred, y_prob):
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else None,
        }

    results = {
        "logistic_regression": eval_clf(y_test, log_pred, log_prob),
        "lightgbm_classifier": eval_clf(y_test, lgb_pred, lgb_prob),
    }

    joblib.dump(lgb_clf, models_dir / "lgb_classifier_bloom.joblib")
    logger.info(
        f"Результаты классификации Bloom Risk (Test Set): "
        f"LightGBM F1={results['lightgbm_classifier']['f1_score']:.3f}, "
        f"ROC-AUC={results['lightgbm_classifier']['roc_auc']:.3f}"
    )
    return results


def run_training_pipeline(project_root: Path) -> None:
    data_path = project_root / "data" / "processed" / "features_dataset.parquet"
    models_dir = project_root / "src" / "models" / "saved_models"
    metrics_path = project_root / "data" / "processed" / "model_metrics.json"

    models_dir.mkdir(parents=True, exist_ok=True)
    train_df, test_df = load_and_split_data(data_path, split_date="2024-01-01")

    logger.info(">>> 1. Обучение регрессионных моделей прогноза Chl-a...")
    reg_metrics = train_regression_models(train_df, test_df, models_dir)

    logger.info(">>> 2. Обучение классификаторов риска цветения (Bloom Risk)...")
    clf_metrics = train_classification_models(train_df, test_df, models_dir)

    full_report = {
        "dataset_split": {
            "train_period": "2020-01-01 to 2023-12-31",
            "test_period": "2024-01-01 to 2025-12-31",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
        },
        "regression_results": reg_metrics,
        "classification_results": clf_metrics,
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    logger.info(f"Метрики моделей сохранены в {metrics_path}")


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    root = current_dir.parent.parent
    run_training_pipeline(root)
