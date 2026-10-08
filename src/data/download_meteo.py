"""Модуль автоматической загрузки метеорологических данных через NASA POWER API.

Загружает суточные ряды для заданных географических координат водных объектов:
- T2M, T2M_MAX, T2M_MIN: температура воздуха (°C)
- WS2M: скорость ветра (м/с) - критична для оценки штилевых условий всплытия цианобактерий
- PRECTOTCORR: сумма осадков (мм/день) - смыв биогенов с водосбора
- ALLSKY_SFC_SW_DWN: суммарная солнечная радиация (МДж/м²/день) - фотосинтетическая активность
- RH2M: относительная влажность воздуха (%)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_nasa_power_daily(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    parameters: list[str]
) -> Dict[str, Any]:
    """Выполняет запрос к открытому REST API NASA POWER."""
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    # Формат дат для NASA POWER: YYYYMMDD
    start_str = start_date.replace("-", "")
    end_str = end_date.replace("-", "")

    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": start_str,
        "end": end_str,
        "format": "JSON",
        "header": "true",
    }

    logger.info(f"Запрос к NASA POWER API: lat={lat}, lon={lon}, период={start_str}-{end_str}")
    response = requests.get(base_url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_nasa_power_response(data: Dict[str, Any], water_body_id: str) -> pd.DataFrame:
    """Преобразует JSON-ответ NASA POWER в структурированный DataFrame."""
    properties = data.get("properties", {})
    parameter_dict = properties.get("parameter", {})

    if not parameter_dict:
        raise ValueError("В ответе NASA POWER отсутствуют параметры данных.")

    # Получаем все доступные даты
    first_param = next(iter(parameter_dict.values()))
    dates = sorted(list(first_param.keys()))

    records = []
    for d_str in dates:
        # Дата в формате YYYYMMDD -> YYYY-MM-DD
        date_formatted = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
        row = {"water_body_id": water_body_id, "date": date_formatted}
        for param_name, values in parameter_dict.items():
            val = values.get(d_str)
            # В NASA POWER спецзначения типа -999.0 обозначают отсутствие данных
            row[param_name] = None if val is None or val <= -900 else float(val)
        records.append(row)

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


def download_all_water_bodies(config_path: Path, output_dir: Path) -> None:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_cfg = config.get("project", {}).get("date_range", {})
    start_date = date_cfg.get("start_date", "2020-01-01")
    end_date = date_cfg.get("end_date", "2025-12-31")

    meteo_vars = list(config.get("meteo_parameters", {}).get("variables", {}).keys())
    water_bodies = config.get("water_bodies", {})

    all_dfs = []

    for key, wb_info in water_bodies.items():
        wb_id = wb_info["id"]
        wb_name = wb_info["name_ru"]
        coords = wb_info["coordinates"]
        lat, lon = coords["lat"], coords["lon"]

        raw_json_path = output_dir / f"{key}_raw.json"
        csv_path = output_dir / f"{key}_daily_meteo.csv"

        logger.info(f"Обработка объекта: {wb_name} ({wb_id})...")

        try:
            if raw_json_path.exists():
                logger.info(f"Загрузка из локального кэша {raw_json_path}")
                with open(raw_json_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            else:
                raw_data = fetch_nasa_power_daily(lat, lon, start_date, end_date, meteo_vars)
                with open(raw_json_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, ensure_ascii=False, indent=2)

            df = parse_nasa_power_response(raw_data, wb_id)
            df.to_csv(csv_path, index=False)
            logger.info(f"Сохранено {len(df)} записей в {csv_path}")
            all_dfs.append(df)
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных для {wb_name}: {e}", exc_info=True)

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_path = output_dir.parent.parent / "processed" / "combined_meteo.parquet"
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_parquet(combined_path, index=False)
        logger.info(f"Объединенный файл сохранен в {combined_path} ({len(combined_df)} строк)")


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    config_file = project_root / "configs" / "water_bodies.yaml"
    out_dir = project_root / "data" / "raw" / "meteo"

    download_all_water_bodies(config_file, out_dir)
