"""Генератор интерактивного автономного веб-дашборда системы раннего предупреждения эвтрофикации.

Создает HTML-дашборд с:
1. Интерактивной картой Leaflet (Заславское вдхр. и озеро Нарочь) с индикаторами рисков.
2. Графиками временных рядов Chl-a за 2024-2025 гг. и пороговой линией цветения (25 мкг/л).
3. Карточками раннего предупреждения Explainable AI на основе Графа знаний и норм Беларуси.
"""

import json
import sys
from pathlib import Path
import pandas as pd

# Добавляем корень проекта в путь поиска модулей
project_root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_dir) not in sys.path:
    sys.path.insert(0, str(project_root_dir))

try:
    from src.api.main import predict_water_body, CONFIG
except ImportError:
    from water_eutrophication.src.api.main import predict_water_body, CONFIG


def create_standalone_dashboard(output_file: Path) -> None:
    # Получаем свежие вердикты графа знаний для обоих объектов
    verdict_zaslav = predict_water_body("BY_RES_001", date="2025-07-21")
    verdict_naroch = predict_water_body("BY_LAKE_001", date="2025-07-21")

    # Читаем данные временных рядов за 2024-2025 гг.
    df = pd.read_parquet(output_file.parent / "features_dataset.parquet")
    df_recent = df[df["date"] >= "2024-01-01"].copy()

    zaslav_series = df_recent[df_recent["water_body_id"] == "BY_RES_001"].sort_values("date")
    naroch_series = df_recent[df_recent["water_body_id"] == "BY_LAKE_001"].sort_values("date")

    zaslav_dates = [str(d)[:10] for d in zaslav_series["date"]]
    zaslav_chla = [float(x) for x in zaslav_series["target_chl_a_next_10d"]]

    naroch_dates = [str(d)[:10] for d in naroch_series["date"]]
    naroch_chla = [float(x) for x in naroch_series["target_chl_a_next_10d"]]

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг и раннее предупреждение эвтрофикации (Беларусь)</title>
    <!-- Подключение Leaflet и Chart.js из надежного CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --red-alert: #ef4444;
            --yellow-alert: #f59e0b;
            --green-alert: #10b981;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 26px;
            color: var(--accent-blue);
        }}
        .header p {{
            margin: 0;
            color: var(--text-muted);
            font-size: 15px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 900px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge-red {{ background: rgba(239, 68, 68, 0.2); color: var(--red-alert); border: 1px solid var(--red-alert); }}
        .badge-yellow {{ background: rgba(245, 158, 11, 0.2); color: var(--yellow-alert); border: 1px solid var(--yellow-alert); }}
        .badge-green {{ background: rgba(16, 185, 129, 0.2); color: var(--green-alert); border: 1px solid var(--green-alert); }}
        .metric-row {{
            display: flex;
            gap: 16px;
            margin: 16px 0;
        }}
        .metric-box {{
            flex: 1;
            background: rgba(15, 23, 42, 0.6);
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border);
        }}
        .metric-val {{
            font-size: 22px;
            font-weight: bold;
            color: #fff;
        }}
        .metric-label {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .reasons-list, .actions-list {{
            margin: 8px 0;
            padding-left: 20px;
            font-size: 14px;
            color: #cbd5e1;
        }}
        .actions-list li {{
            margin-bottom: 6px;
            color: #38bdf8;
        }}
        #map {{
            height: 380px;
            border-radius: 8px;
            width: 100%;
        }}
        .chart-container {{
            position: relative;
            height: 340px;
            width: 100%;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Интеллектуальная система раннего предупреждения эвтрофикации водных объектов</h1>
        <p>Исследовательский прототип для Республики Беларусь | Пилотный полигон: Заславское вдхр. и озеро Нарочь</p>
    </div>

    <div class="grid">
        <!-- Карточка: Заславское -->
        <div class="card">
            <h2>
                <span>{verdict_zaslav.water_body_name}</span>
                <span class="badge badge-red">РИСК: {verdict_zaslav.alert_level}</span>
            </h2>
            <div class="metric-row">
                <div class="metric-box">
                    <div class="metric-val">{verdict_zaslav.predicted_chl_a_ug_l} мкг/л</div>
                    <div class="metric-label">Прогноз Chl-a (через 10 дн)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val">{verdict_zaslav.bloom_probability * 100:.1f}%</div>
                    <div class="metric-label">P(Цветение)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val">{verdict_zaslav.trophic_index_tsi} ({verdict_zaslav.trophic_class})</div>
                    <div class="metric-label">Индекс Карлсона (TSI)</div>
                </div>
            </div>
            <h4>Объяснение причин (Knowledge Graph Inference):</h4>
            <ul class="reasons-list">
                {"".join(f"<li>{r}</li>" for r in verdict_zaslav.reasons)}
            </ul>
            <h4>Рекомендуемые меры (СанПиН / Минприроды РБ):</h4>
            <ul class="actions-list">
                {"".join(f"<li>{a}</li>" for a in verdict_zaslav.recommended_actions)}
            </ul>
        </div>

        <!-- Карточка: Нарочь -->
        <div class="card">
            <h2>
                <span>{verdict_naroch.water_body_name}</span>
                <span class="badge badge-yellow">РИСК: {verdict_naroch.alert_level}</span>
            </h2>
            <div class="metric-row">
                <div class="metric-box">
                    <div class="metric-val">{verdict_naroch.predicted_chl_a_ug_l} мкг/л</div>
                    <div class="metric-label">Прогноз Chl-a (через 10 дн)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val">{verdict_naroch.bloom_probability * 100:.1f}%</div>
                    <div class="metric-label">P(Цветение)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val">{verdict_naroch.trophic_index_tsi} ({verdict_naroch.trophic_class})</div>
                    <div class="metric-label">Индекс Карлсона (TSI)</div>
                </div>
            </div>
            <h4>Объяснение причин (Knowledge Graph Inference):</h4>
            <ul class="reasons-list">
                {"".join(f"<li>{r}</li>" for r in verdict_naroch.reasons)}
            </ul>
            <h4>Рекомендуемые меры (СанПиН / Минприроды РБ):</h4>
            <ul class="actions-list">
                {"".join(f"<li>{a}</li>" for a in verdict_naroch.recommended_actions)}
            </ul>
        </div>
    </div>

    <div class="grid">
        <!-- Интерактивная карта водоемов Беларуси -->
        <div class="card">
            <h2>Геоинформационный модуль мониторинга (Беларусь)</h2>
            <div id="map"></div>
        </div>

        <!-- Графики динамики хлорофилла-a -->
        <div class="card">
            <h2>Временные ряды хлорофилла-a (2024–2025 гг.)</h2>
            <div class="chart-container">
                <canvas id="timeSeriesChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // Инициализация карты Leaflet с поддержкой надежных тайловых провайдеров
        const map = L.map('map', {{
            center: [54.42, 27.10],
            zoom: 8,
            scrollWheelZoom: true
        }});

        // Провайдер 1: OpenStreetMap (Стандартный глобальный надежный источник)
        const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
        }});

        // Провайдер 2: Спутниковые снимки Esri World Imagery (высокое разрешение для водных объектов)
        const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 18,
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }});

        // Провайдер 3: Топографическая гидрологическая карта Esri Topo
        const esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 18,
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, METI, MapmyIndia'
        }});

        // По умолчанию активируем спутниковый слой (идеально для мониторинга цветения)
        esriSatellite.addTo(map);

        // Переключатель базовых карт
        const baseMaps = {{
            "🛰️ Спутник (Esri World Imagery)": esriSatellite,
            "🗺️ OpenStreetMap": osmLayer,
            "⛰️ Топографическая карта": esriTopo
        }};
        L.control.layers(baseMaps, null, {{ position: 'topright' }}).addTo(map);

        // Полигон акватории: Заславское вдхр. (Bounding Box)
        const zaslavBounds = [[53.94, 27.28], [54.02, 27.46]];
        L.rectangle(zaslavBounds, {{
            color: "#ef4444",
            weight: 2,
            fillColor: "#ef4444",
            fillOpacity: 0.25,
            dashArray: "4, 4"
        }}).addTo(map).bindTooltip("Акватория: Заславское вдхр.", {{ permanent: false }});

        // Маркер: Заславское вдхр (Минское море)
        const m1 = L.circleMarker([53.985, 27.380], {{
            radius: 12,
            color: '#ffffff',
            weight: 2,
            fillColor: '#ef4444',
            fillOpacity: 0.95
        }}).addTo(map);
        m1.bindPopup(`
            <div style="color: #0f172a; min-width: 200px;">
                <h4 style="margin: 0 0 6px 0; color: #dc2626;">Заславское вдхр. (Минское море)</h4>
                <b>Статус:</b> <span style="color: #dc2626; font-weight: bold;">RED (Высокий риск)</span><br>
                <b>Прогноз Chl-a:</b> {verdict_zaslav.predicted_chl_a_ug_l} мкг/л<br>
                <b>Вероятность цветения:</b> {verdict_zaslav.bloom_probability * 100:.1f}%<br>
                <b>Глубина:</b> 3.5 м (мелководное)
            </div>
        `).bindTooltip("Заславское вдхр. (РИСК: RED)", {{ permanent: true, direction: "top", offset: [0, -10] }});

        // Полигон акватории: Озеро Нарочь (Bounding Box)
        const narochBounds = [[54.80, 26.68], [54.93, 26.92]];
        L.rectangle(narochBounds, {{
            color: "#38bdf8",
            weight: 2,
            fillColor: "#38bdf8",
            fillOpacity: 0.2,
            dashArray: "4, 4"
        }}).addTo(map).bindTooltip("Акватория: Озеро Нарочь", {{ permanent: false }});

        // Маркер: Нарочь
        const m2 = L.circleMarker([54.850, 26.780], {{
            radius: 12,
            color: '#ffffff',
            weight: 2,
            fillColor: '#f59e0b',
            fillOpacity: 0.95
        }}).addTo(map);
        m2.bindPopup(`
            <div style="color: #0f172a; min-width: 200px;">
                <h4 style="margin: 0 0 6px 0; color: #d97706;">Озеро Нарочь</h4>
                <b>Статус:</b> <span style="color: #d97706; font-weight: bold;">YELLOW (Мезотрофный)</span><br>
                <b>Прогноз Chl-a:</b> {verdict_naroch.predicted_chl_a_ug_l} мкг/л<br>
                <b>Вероятность цветения:</b> {verdict_naroch.bloom_probability * 100:.1f}%<br>
                <b>Глубина:</b> 8.9 м (макс. 24.8 м)
            </div>
        `).bindTooltip("Озеро Нарочь (РИСК: YELLOW)", {{ permanent: true, direction: "top", offset: [0, -10] }});

        // Автоматическая подгонка размеров при загрузке страницы (устраняет эффект серой сетки)
        setTimeout(() => {{ map.invalidateSize(); }}, 300);
        window.addEventListener('resize', () => {{ map.invalidateSize(); }});

        // График временных рядов Chart.js
        const ctx = document.getElementById('timeSeriesChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(zaslav_dates)},
                datasets: [
                    {{
                        label: 'Заславское вдхр. (Chl-a, мкг/л)',
                        data: {json.dumps(zaslav_chla)},
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.3,
                        borderWidth: 2
                    }},
                    {{
                        label: 'Озеро Нарочь (Chl-a, мкг/л)',
                        data: {json.dumps(naroch_chla)},
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.1)',
                        tension: 0.3,
                        borderWidth: 2
                    }},
                    {{
                        label: 'Порог цветения (25 мкг/л)',
                        data: new Array({len(zaslav_dates)}).fill(25.0),
                        borderColor: '#eab308',
                        borderDash: [5, 5],
                        borderWidth: 1.5,
                        pointRadius: 0
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        title: {{ display: true, text: 'Хлорофилл-a (мкг/л)', color: '#94a3b8' }},
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#1e293b' }},
                        ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }}
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#f8fafc' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Дашборд успешно сгенерирован: {output_file}")


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    root = current_dir.parent.parent
    dash_path = root / "data" / "processed" / "dashboard.html"
    create_standalone_dashboard(dash_path)
