"""FastAPI сервис интеллектуальной системы мониторинга и прогнозирования эвтрофикации.

Предоставляет REST API для аналитиков и интеграции с геопорталами:
- /water-bodies: список пилотных водных объектов Беларуси
- /metrics: метрики качества ML-моделей (LightGBM vs Baselines)
- /predict/{water_body_id}: прогноз на 10 дней вперед + вывод экспертных правил графа знаний
- /sparql: выполнение SPARQL-запросов к RDF графу знаний
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
import yaml
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

try:
    from src.knowledge_graph.graph_engine import (
        WaterKnowledgeGraphEngine,
    )
    from src.models.train_models import FEATURE_COLS
except ImportError:
    from water_eutrophication.src.knowledge_graph.graph_engine import (
        WaterKnowledgeGraphEngine,
    )
    from water_eutrophication.src.models.train_models import FEATURE_COLS

app = FastAPI(
    title="Система раннего предупреждения эвтрофикации водных объектов Беларуси",
    description="Интеллектуальная система (ML + Граф знаний) для Заславского водохранилища и озера Нарочь",
    version="1.0.0",
)

# Инициализация путей
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "water_bodies.yaml"
MODELS_DIR = PROJECT_ROOT / "src" / "models" / "saved_models"
FEATURES_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features_dataset.parquet"
METRICS_PATH = PROJECT_ROOT / "data" / "processed" / "model_metrics.json"
ONTOLOGY_PATH = PROJECT_ROOT / "src" / "knowledge_graph" / "ontology.ttl"

# Загрузка ресурсов в память
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

LGB_REGRESSOR = joblib.load(MODELS_DIR / "lgb_regressor_chla.joblib")
LGB_CLASSIFIER = joblib.load(MODELS_DIR / "lgb_classifier_bloom.joblib")
KG_ENGINE = WaterKnowledgeGraphEngine(ONTOLOGY_PATH)


class AlertResponse(BaseModel):
    water_body_id: str
    water_body_name: str
    assessment_date: str
    forecast_horizon_days: int
    predicted_chl_a_ug_l: float
    bloom_probability: float
    trophic_index_tsi: float
    trophic_class: str
    alert_level: str
    reasons: List[str]
    recommended_actions: List[str]


@app.get("/")
def get_root():
    return {
        "system": "Belarus Eutrophication Early Warning Prototype",
        "pilot_water_bodies": [
            "Заславское водохранилище (Минское море)",
            "Озеро Нарочь",
        ],
        "status": "active",
        "version": "1.0.0",
    }


@app.get("/water-bodies")
def get_water_bodies():
    return CONFIG.get("water_bodies", {})


@app.get("/metrics")
def get_metrics():
    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Метрики еще не сформированы.")


@app.get("/predict/{water_body_id}", response_model=AlertResponse)
def predict_water_body(
    water_body_id: str,
    date: Optional[str] = Query(None, description="Дата среза в формате YYYY-MM-DD (по умолчанию последняя доступная)"),
):
    # Поиск водоема в конфиге
    wb_cfg = None
    for wb in CONFIG.get("water_bodies", {}).values():
        if wb["id"] == water_body_id:
            wb_cfg = wb
            break

    if not wb_cfg:
        raise HTTPException(status_code=404, detail=f"Водоем с ID '{water_body_id}' не найден.")

    df = pd.read_parquet(FEATURES_DATA_PATH)
    sub = df[df["water_body_id"] == water_body_id].sort_values("date").reset_index(drop=True)

    if len(sub) == 0:
        raise HTTPException(status_code=404, detail=f"Нет данных наблюдений для '{water_body_id}'.")

    if date:
        row_match = sub[sub["date"].astype(str).str.startswith(date)]
        if len(row_match) == 0:
            raise HTTPException(status_code=404, detail=f"Дата {date} не найдена в наблюдениях.")
        row = row_match.iloc[-1]
    else:
        # Берем последнее доступное наблюдение (например, пиковый летний срез)
        row = sub.iloc[-1]

    # Формируем вектор признаков с корректным числовым типом
    feature_dict = {col: float(row[col]) for col in FEATURE_COLS}
    X = pd.DataFrame([feature_dict])

    # ML-прогноз
    pred_chl_a = float(LGB_REGRESSOR.predict(X)[0])
    pred_chl_a = max(0.5, round(pred_chl_a, 2))

    pred_prob = float(LGB_CLASSIFIER.predict_proba(X)[0, 1])
    pred_prob = round(pred_prob, 3)

    # Семантический вывод через Граф знаний
    verdict = KG_ENGINE.evaluate_water_body(
        water_body_id=water_body_id,
        water_body_name=wb_cfg["name_ru"],
        is_reservoir=(wb_cfg["type"] == "reservoir"),
        date_str=str(row["date"])[:10],
        predicted_chl_a=pred_chl_a,
        bloom_probability=pred_prob,
        temp_mean_14d=float(row["temp_mean_14d"]),
        calm_fraction_7d=float(row["calm_fraction_7d"]),
        current_chl_a=float(row["chl_a_current"]),
    )

    return AlertResponse(
        water_body_id=water_body_id,
        water_body_name=verdict.water_body_name,
        assessment_date=verdict.assessment_date,
        forecast_horizon_days=10,
        predicted_chl_a_ug_l=verdict.predicted_chl_a,
        bloom_probability=verdict.bloom_probability,
        trophic_index_tsi=verdict.trophic_index,
        trophic_class=verdict.trophic_class,
        alert_level=verdict.alert_level,
        reasons=verdict.reasons,
        recommended_actions=verdict.recommended_actions,
    )
