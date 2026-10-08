# 🌊 Интеллектуальная система мониторинга, прогнозирования и раннего предупреждения риска эвтрофикации водных объектов Беларуси (КИТС)

> **Комплексная интеллектуальная технология и система (КИТС) экологического мониторинга**  
> *Пилотные водные объекты: Заславское водохранилище (Минское море), Цнянское водохранилище (Цнянка), озеро Нарочь.*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.5+-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Semantic Web](https://img.shields.io/badge/W3C-RDF%20%7C%20OWL%20%7C%20SPARQL-orange.svg)](https://www.w3.org/standards/semanticweb/)
[![Web GIS](https://img.shields.io/badge/Web--GIS-Leaflet%20%7C%20Esri-green.svg)](https://leafletjs.com/)

---

## 📌 Описание проекта

Проект представляет собой прототип интеллектуальной системы раннего предупреждения эвтрофикации поверхностных водных объектов Республики Беларусь. Система объединяет методы дистанционного зондирования Земли (ДЗЗ), машинного обучения (Gradient Boosting) и символьного искусственного интеллекта (Графы знаний и правила СанПиН РБ) в рамках концепции **Neuro-Symbolic AI / Explainable AI (XAI)**.

### Ключевые возможности:
1. **Сбор и предобработка данных (ETL):** автоматизированная загрузка суточных гидрометеорологических параметров (NASA POWER API) и спутниковых оптических спектральных данных (Copernicus Global Land Service LWQ 100m, Sentinel-2 proxy) за 2020–2025 гг.
2. **Инженерия признаков (Feature Engineering):** расчет 28 признаков, включая скользящие окна (7, 14, 30 дней) для моделирования термической инерции водной массы, индикаторы штилевых условий, кумулятивные осадки биогенного смыва и циклическое кодирование сезонности.
3. **Предиктивное моделирование (Machine Learning):**
   - **Регрессия концентрации хлорофилла-a:** LightGBM Regressor ($R^2 = 0.880$, $\text{RMSE} = 3.64\ \text{мкг/л}$).
   - **Классификация риска цветения цианобактерий:** LightGBM Classifier ($\text{ROC-AUC} = 0.978$, $\text{Recall} = 0.923$).
4. **База знаний и семантический логический вывод (Knowledge Graph & Rules):**
   - Онтология качества поверхностных вод на базе международного стандарта **W3C SOSA/SSN**.
   - Продукционные правила на основе **СанПиН Республики Беларусь** (санитарный порог $25\ \text{мкг/л}$) и логарифмического индекса трофического состояния Карлсона ($TSI$).
   - Формирование объяснимых вердиктов (`AlertVerdict`) с перечнем причин и регламентных природоохранных мер.
   - Поддержка семантических запросов **SPARQL**.
5. **Сервисный уровень (REST API):** асинхронный сервис на **FastAPI** с валидацией схем **Pydantic** и интерактивной документацией **Swagger UI** (`/docs`).
6. **Интерактивный Web-ГИС дашборд:** автономная аналитическая панель на базе **Leaflet.js** (космические снимки Esri World Imagery, полигоны акваторий Bounding Box) и **Chart.js** (динамика временных рядов 2024–2025 гг. с пороговыми линиями риска).

---

## 🏛️ Архитектура системы

```
    ┌──────────────────────┐       ┌──────────────────────┐
    │    NASA POWER API    │       │ Copernicus LWQ (100m)│
    │ (Метеопараметры)     │       │ (Спутниковый Chl-a)  │
    └──────────┬───────────┘       └──────────┬───────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │  ETL & Feature Engineering   │
               │ (Rolling windows, Lags, DOY) │
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │    Machine Learning Layer    │
               │  (LightGBM Regr + Classif)   │
               └──────────────┬───────────────┘
                              ▼ Прогнозы Chl-a & P(Bloom)
               ┌──────────────────────────────┐
               │    Semantic Knowledge Base   │
               │  (W3C SOSA/SSN + СанПиН РБ)  │
               │    + Движок правил rdflib    │
               └──────────────┬───────────────┘
                              ▼ Объяснимый AlertVerdict
               ┌──────────────────────────────┐
               │      FastAPI REST Service    │
               │   (/predict, /metrics, etc.) │
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │    Web GIS Dashboard HTML    │
               │    (Leaflet.js + Chart.js)   │
               └──────────────────────────────┘
```

---

## 📁 Структура репозитория

```text
├── configs/
│   └── water_bodies.yaml        # Конфигурация пилотных объектов (координаты, морфометрия)
├── data/
│   ├── raw/                     # Исходные спутниковые и метеоданные
│   └── processed/               # Обработанные датасеты Parquet, метрики и дашборд
│       ├── dashboard.html       # Готовый интерактивный Web-ГИС дашборд
│       ├── features_dataset.parquet
│       ├── knowledge_graph_snapshot.ttl
│       └── model_metrics.json
├── docs/
│   ├── 00_OVERVIEW_AND_MAPPING.md
│   ├── REPRODUCIBILITY_GUIDE.md # Руководство по воспроизводимости
│   └── tutorials/               # Полный образовательный курс из 20 гайдов
│       ├── 01_venv_and_dependencies.md ... 20_chart_js_visualization.md
│       └── README.md
├── notebooks/                   # Jupyter ноутбуки для исследовательского анализа
├── src/
│   ├── api/
│   │   ├── main.py              # Сервер FastAPI и эндпоинты
│   │   └── generate_dashboard.py# Генератор Web-ГИС дашборда
│   ├── data/
│   │   ├── download_meteo.py    # ETL пайплайн NASA POWER
│   │   └── satellite_processor.py # Обработка спутниковых данных ДЗЗ
│   ├── features/
│   │   └── build_features.py    # Расчет признаков и скользящих окон
│   ├── knowledge_graph/
│   │   ├── ontology.ttl         # Онтология предметной области (W3C SOSA/SSN)
│   │   └── graph_engine.py      # Движок базы знаний, правила СанПиН и SPARQL
│   └── models/
│       ├── train_models.py      # Обучение и валидация моделей LightGBM
│       └── saved_models/        # Сериализованные модели joblib
├── requirements.txt             # Список зависимостей Python
└── .gitignore
```

---

## 🚀 Быстрый старт (Quickstart)

### 1. Клонирование репозитория и установка окружения
```bash
git clone https://github.com/shinigam2/kits_for_cinyanka.git
cd kits_for_cinyanka

# Создание и активация виртуального окружения
python3 -m venv .venv
source .venv/bin/activate  # Для Linux/macOS
# .venv\Scripts\activate   # Для Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Запуск REST API сервиса
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
- Документация **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- Альтернативная документация **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Просмотр интерактивного дашборда
Откройте файл в любом современном браузере:
```bash
xdg-open data/processed/dashboard.html  # Linux
# open data/processed/dashboard.html    # macOS
# start data/processed/dashboard.html   # Windows
```

---

## 📊 Результаты и метрики моделей

Валидация проводилась по схеме **Out-of-Time split** (обучение на данных 2020–2023 гг., тестирование на 2024–2025 гг.):

| Модель | Целевая переменная | Метрика качества | Значение |
| :--- | :--- | :--- | :---: |
| **LightGBM Regressor** | Хлорофилл-a ($Chl\text{-}a$, мкг/л) | Коэффициент детерминации ($R^2$) | **0.880** |
| | | Среднеквадратическая ошибка ($\text{RMSE}$) | **3.64** |
| | | Средняя абсолютная ошибка ($\text{MAE}$) | **2.62** |
| **LightGBM Classifier** | Риск цветения ($Chl\text{-}a \ge 25$) | Площадь под ROC-кривой ($\text{ROC-AUC}$) | **0.978** |
| | | Полнота выявления вспышек ($\text{Recall}$) | **0.923** |
| | | Точность прогноза ($\text{Precision}$) | **0.900** |

---

## 📚 Образовательный курс (20 технологий)

В папке [`docs/tutorials/`](docs/tutorials/) содержится подробный пошаговый курс, раскрывающий устройство каждой технологии проекта: от основ Python до графов знаний и веб-картографии.  
Оглавление курса доступно в [docs/tutorials/README.md](docs/tutorials/README.md).

---

## 📜 Лицензия и использование

Проект разработан в академических и исследовательских целях для мониторинга поверхностных водоёмов Беларуси. Свободно для использования в некоммерческих и образовательных проектах.
