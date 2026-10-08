"""Модуль генерации признаков (Feature Engineering) для прогнозирования эвтрофикации.

Объединяет суточные метеоданные (NASA POWER) и декадные спутниковые ряды (Copernicus LWQ).
Формирует признаки:
1. Авторегрессионные (текущий Chl-a, лаг -10д, скорость прироста d_Chl).
2. Накопленные тепловые и гидродинамические факторы (скользящие средние T2M за 7, 14, 21 день, дни с T > 20°C).
3. Биогенно-осадочные факторы (сумма осадков за 7 и 14 дней - смыв биогенов с водосбора).
4. Световые и штилевые триггеры (инсоляция за 7 дней, доля штилевых дней со скоростью ветра < 2.2 м/с).
5. Календарно-сезонные гармоники (sin/cos дня года).
6. Морфометрические свойства водоёма (средняя глубина, площадь зеркала).

Целевые переменные:
- `target_chl_a_next_10d`: концентрация Chl-a на следующем шаге (через 10 дней), мкг/л.
- `target_bloom_risk_next_10d`: бинарный флаг риска цветения (1 если Chl-a >= 25 мкг/л).
"""

import logging
import math
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_feature_table(
    meteo_df: pd.DataFrame,
    sat_df: pd.DataFrame,
    water_bodies_cfg: Dict[str, Any]
) -> pd.DataFrame:
    """Формирует объединенную витрину признаков для машинного обучения."""
    meteo_df["date"] = pd.to_datetime(meteo_df["date"])
    sat_df["date"] = pd.to_datetime(sat_df["date"])

    all_rows = []

    for wb_key, wb_info in water_bodies_cfg.items():
        wb_id = wb_info["id"]
        morph = wb_info["morphometry"]
        mean_depth = morph["mean_depth_m"]
        area_km2 = morph["surface_area_km2"]
        is_reservoir = 1 if wb_info["type"] == "reservoir" else 0

        sub_m = meteo_df[meteo_df["water_body_id"] == wb_id].sort_values("date").set_index("date")
        sub_s = sat_df[sat_df["water_body_id"] == wb_id].sort_values("date").reset_index(drop=True)

        # Вычисляем признаки для каждого спутникового наблюдения
        for i in range(len(sub_s)):
            current_obs = sub_s.iloc[i]
            cur_date = current_obs["date"]

            # Таргет - следующее спутниковое наблюдение (через 10 дней)
            if i + 1 < len(sub_s):
                next_obs = sub_s.iloc[i + 1]
                target_chl = next_obs["chl_a_ug_l"]
                target_bloom = int(target_chl >= 25.0)
            else:
                target_chl = np.nan
                target_bloom = np.nan

            # Лаг текущего хлорофилла и лаг предыдущего (10 дней назад)
            cur_chl = current_obs["chl_a_ug_l"]
            prev_chl = sub_s.iloc[i - 1]["chl_a_ug_l"] if i > 0 else cur_chl
            chl_diff = cur_chl - prev_chl

            # Извлекаем окно метеоданных до текущей даты включительно
            # 7, 14, 21 день
            m_window_7 = sub_m.loc[cur_date - pd.Timedelta(days=7):cur_date]
            m_window_14 = sub_m.loc[cur_date - pd.Timedelta(days=14):cur_date]
            m_window_21 = sub_m.loc[cur_date - pd.Timedelta(days=21):cur_date]

            if len(m_window_7) == 0:
                continue

            temp_mean_7d = m_window_7["T2M"].mean()
            temp_max_7d = m_window_7["T2M_MAX"].max()
            temp_mean_14d = m_window_14["T2M"].mean()
            temp_mean_21d = m_window_21["T2M"].mean()

            # Дни с жарой > 20°C за последние 14 дней
            hot_days_14d = (m_window_14["T2M_MAX"] >= 22.0).sum()

            # Сумма осадков (смыв биогенов)
            precip_sum_7d = m_window_7["PRECTOTCORR"].sum()
            precip_sum_14d = m_window_14["PRECTOTCORR"].sum()

            # Солнечная радиация
            radiation_mean_7d = m_window_7["ALLSKY_SFC_SW_DWN"].mean()

            # Штиль (скорость ветра < 2.2 м/с способствует всплытию цианобактерий)
            calm_fraction_7d = (m_window_7["WS2M"] < 2.2).mean()
            wind_mean_7d = m_window_7["WS2M"].mean()

            # Календарные признаки
            doy = cur_date.dayofyear
            sin_doy = math.sin(2 * math.pi * doy / 365.25)
            cos_doy = math.cos(2 * math.pi * doy / 365.25)

            row = {
                "water_body_id": wb_id,
                "water_body_name": wb_info["name_ru"],
                "date": cur_date,
                "month": cur_date.month,
                "day_of_year": doy,
                "sin_doy": sin_doy,
                "cos_doy": cos_doy,
                # Морфометрия
                "mean_depth_m": mean_depth,
                "surface_area_km2": area_km2,
                "is_reservoir": is_reservoir,
                # Текущие оптические показатели
                "chl_a_current": cur_chl,
                "chl_a_lag10d": prev_chl,
                "chl_a_growth_10d": chl_diff,
                "turbidity_current": current_obs["turbidity_ntu"],
                "tsi_current": current_obs["tsi_carson"],
                "quality_flag": current_obs["quality_flag"],
                # Метеорологические факторы влияния
                "temp_mean_7d": round(temp_mean_7d, 2),
                "temp_max_7d": round(temp_max_7d, 2),
                "temp_mean_14d": round(temp_mean_14d, 2),
                "temp_mean_21d": round(temp_mean_21d, 2),
                "hot_days_14d": int(hot_days_14d),
                "precip_sum_7d": round(precip_sum_7d, 2),
                "precip_sum_14d": round(precip_sum_14d, 2),
                "radiation_mean_7d": round(radiation_mean_7d, 2),
                "calm_fraction_7d": round(calm_fraction_7d, 2),
                "wind_mean_7d": round(wind_mean_7d, 2),
                # Таргеты на t + 10 дней
                "target_chl_a_next_10d": target_chl,
                "target_bloom_risk_next_10d": target_bloom,
            }
            all_rows.append(row)

    df_features = pd.DataFrame(all_rows)
    # Исключаем последнюю точку каждого ряда, где нет таргета
    df_features = df_features.dropna(subset=["target_chl_a_next_10d"]).reset_index(drop=True)
    return df_features


def run_feature_engineering(project_root: Path) -> None:
    config_path = project_root / "configs" / "water_bodies.yaml"
    meteo_path = project_root / "data" / "processed" / "combined_meteo.parquet"
    sat_path = project_root / "data" / "processed" / "combined_satellite.parquet"
    out_path = project_root / "data" / "processed" / "features_dataset.parquet"

    config = load_config(config_path)
    meteo_df = pd.read_parquet(meteo_path)
    sat_df = pd.read_parquet(sat_path)

    logger.info("Построение витрины признаков...")
    feat_df = build_feature_table(meteo_df, sat_df, config["water_bodies"])

    feat_df.to_parquet(out_path, index=False)
    # Также сохраняем CSV для наглядного просмотра аналитиком
    feat_df.to_csv(out_path.with_suffix(".csv"), index=False)
    logger.info(f"Витрина успешно сохранена в {out_path} ({len(feat_df)} строк, {len(feat_df.columns)} признаков)")


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    root = current_dir.parent.parent
    run_feature_engineering(root)
