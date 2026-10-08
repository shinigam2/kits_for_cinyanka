# Учебный курс: Интеллектуальная система мониторинга и раннего предупреждения эвтрофикации водных объектов Беларуси

Полный пошаговый образовательный курс от нуля до создания интеллектуальной геоинформационной системы (Data Science, Machine Learning, Semantic Web, Web GIS).

Курс разработан на примере пилотных водных объектов Республики Беларусь:
- **Заславское водохранилище (Минское море)** — эвтрофный мелководный модельный водоём.
- **Озеро Нарочь** — олиго-/мезотрофный глубоководный эталонный водоём.

---

## 🗺️ Карта учебного курса (20 технологий)

### Этап 1: Окружение и базовая архитектура проекта
* [01. Виртуальные окружения (venv) и управление зависимостями](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/01_venv_and_dependencies.md)
* [02. Декларативная конфигурация приложения (YAML и 12-Factor App)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/02_yaml_configuration.md)
* [03. Геоданные, географические координаты (WGS-84) и Bounding Box](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/03_geodata_and_coordinates.md)

### Этап 2: Сбор данных и эффективное хранение (Data Pipelines)
* [04. Протокол HTTP, REST API и библиотека requests (NASA POWER API)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/04_requests_and_rest_api.md)
* [05. Анализ временных рядов в pandas (DateTimeIndex, ресемплинг, фильтрация)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/05_pandas_time_series.md)
* [06. Колоночное хранение данных Apache Parquet и PyArrow](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/06_parquet_and_pyarrow.md)
* [07. Оптическое дистанционное зондирование Земли (Copernicus LWQ, Sentinel-2, Red Edge)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/07_satellite_remote_sensing.md)

### Этап 3: Инженерия признаков и предметная математика (Feature Engineering)
* [08. Скользящие окна (Rolling Windows), лаги и циклическое кодирование времени](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/08_rolling_windows_and_lags.md)
* [09. Индекс трофического состояния Карлсона (TSI) и биофизика эвтрофикации](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/09_trophic_state_index_carlson.md)

### Этап 4: Машинное обучение и сериализация (Machine Learning)
* [10. Валидация временных рядов (Time-based Split, Data Leakage) и метрики (RMSE, ROC-AUC, Recall)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/10_time_series_validation_and_metrics.md)
* [11. Градиентный бустинг над решающими деревьями (LightGBM)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/11_gradient_boosting_lightgbm.md)
* [12. Сериализация моделей машинного обучения (joblib)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/12_model_serialization_joblib.md)

### Этап 5: Граф знаний, онтологии и экспертные системы (Knowledge Graph & XAI)
* [13. Семантическая паутина (Semantic Web), триплеты RDF и онтологии W3C SOSA/SSN](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/13_semantic_web_rdf_and_ontologies.md)
* [14. Программная работа с графами знаний на Python (библиотека rdflib)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/14_rdflib_in_python.md)
* [15. Язык запросов к графам знаний SPARQL](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/15_sparql_query_language.md)
* [16. Экспертные правила и логический вывод (Rule-based Reasoning, СанПиН РБ и Explainable AI)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/16_expert_rules_and_reasoning.md)

### Этап 6: Сервис и пользовательский интерфейс (Service & Dashboard)
* [17. FastAPI и Pydantic (REST API бэкенд, валидация схем и Swagger UI)](file:///home/frolov-pc/antigrophication/docs/tutorials/17_fastapi_and_pydantic.md)
* [18. Uvicorn и стандарт ASGI (Асинхронный веб-сервер для FastAPI)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/18_uvicorn_and_asgi.md)
* [19. Leaflet.js и Web-ГИС картография (Интерактивные спутниковые карты водоёмов Беларуси)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/19_leaflet_js_web_gis.md)
* [20. Chart.js и визуализация временных рядов (Интерактивные графики хлорофилла-а и пороговые линии риска)](file:///home/frolov-pc/antigravity/water_eutrophication/docs/tutorials/20_chart_js_visualization.md)

---

## 🚀 Практический запуск компонентов проекта

### Запуск веб-дашборда системы:
Откройте в браузере сгенерированный файл дашборда:
`file:///home/frolov-pc/antigravity/water_eutrophication/data/processed/dashboard.html`

### Запуск REST API сервера:
```bash
cd /home/frolov-pc/antigravity
source .venv/bin/activate
uvicorn water_eutrophication.src.api.main:app --reload --host 0.0.0.0 --port 8000
```
Интерактивная документация Swagger API доступна по адресу:  
`http://localhost:8000/docs`
