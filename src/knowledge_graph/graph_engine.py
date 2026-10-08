"""Семантический движок графа знаний (Knowledge Graph & Rules Engine).

Реализует:
1. Построение RDF-графа на базе онтологии W3C SOSA/SSN и расширения для Беларуси.
2. Трансляцию прогнозов ML-моделей в семантические факты.
3. Применение логических правил (Expert Rules) с привязкой к СанПиН РБ и индексу Карлсона:
   - RED:   Прогноз Chl-a >= 25 мкг/л или P(Bloom) >= 0.50 -> Высокий риск цветения цианобактерий.
   - YELLOW: 15 <= Chl-a < 25 мкг/л и благоприятные метеоусловия (жара, штиль).
   - GREEN: Нормативное состояние водного объекта.
4. Выполнение SPARQL-запросов для формирования объяснимого отчета (Explainable DSS).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import XSD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BYWATER = Namespace("http://w3id.org/belarus/water-quality#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")


@dataclass
class AlertVerdict:
    water_body_id: str
    water_body_name: str
    assessment_date: str
    predicted_chl_a: float
    bloom_probability: float
    trophic_index: float
    trophic_class: str
    alert_level: str  # GREEN, YELLOW, RED
    reasons: List[str]
    recommended_actions: List[str]


class WaterKnowledgeGraphEngine:
    def __init__(self, ontology_path: Optional[Path] = None):
        self.graph = Graph()
        self.graph.bind("bywater", BYWATER)
        self.graph.bind("sosa", SOSA)
        if ontology_path and ontology_path.exists():
            self.graph.parse(ontology_path, format="turtle")
            logger.info(f"Онтология загружена из {ontology_path}")

    def evaluate_water_body(
        self,
        water_body_id: str,
        water_body_name: str,
        is_reservoir: bool,
        date_str: str,
        predicted_chl_a: float,
        bloom_probability: float,
        temp_mean_14d: float,
        calm_fraction_7d: float,
        current_chl_a: float
    ) -> AlertVerdict:
        """Транслирует ML-прогноз в RDF-факты и выполняет логический вывод правил."""
        # 1. Определение трофического класса по Карлсону (TSI)
        import math
        tsi = round(float(9.81 * math.log(max(0.1, predicted_chl_a)) + 30.6), 1)

        if tsi < 40:
            trophic_class = "Олиготрофный"
        elif tsi < 50:
            trophic_class = "Мезотрофный"
        elif tsi <= 70:
            trophic_class = "Эвтрофный"
        else:
            trophic_class = "Гиперэвтрофный (Критический)"

        # 2. Логический вывод по правилам оценки риска (Правила СанПиН и экологии РБ)
        reasons = []
        actions = []

        if predicted_chl_a >= 25.0 or bloom_probability >= 0.50:
            alert_level = "RED"
            reasons.append(
                f"Прогнозируемая концентрация хлорофилла-a ({predicted_chl_a:.1f} мкг/л) "
                f"превышает санитарно-экологический порог эвтрофикации (25 мкг/л)."
            )
            reasons.append(
                f"Модельная вероятность массового цветения цианобактерий составляет {bloom_probability * 100:.1f}%."
            )
            if calm_fraction_7d > 0.4:
                reasons.append(f"Штилевые условия ({calm_fraction_7d * 100:.0f}% дней без ветра) стимулируют концентрацию колоний в поверхностном слое.")
            if temp_mean_14d > 18.0:
                reasons.append(f"Высокий прогрев водной массы (средняя T за 14 дней = {temp_mean_14d:.1f}°C) ускоряет вегетацию.")

            actions.append("Усилить лабораторный контроль: внеплановый отбор проб на цианотоксины (микроцистины).")
            actions.append("Уведомить территориальные органы Минприроды и санэпиднадзора о риске цветения.")
            actions.append("Рекомендовать ограничение рекреационного водопользования на пляжных зонах.")

        elif predicted_chl_a >= 15.0 or (temp_mean_14d >= 20.0 and calm_fraction_7d >= 0.3):
            alert_level = "YELLOW"
            reasons.append(
                f"Повышенная концентрация хлорофилла-a ({predicted_chl_a:.1f} мкг/л) с тенденцией к росту."
            )
            reasons.append(
                f"Температурный режим ({temp_mean_14d:.1f}°C) благоприятен для активной вегетации фитопланктона."
            )
            actions.append("Увеличить частоту спутникового оптического скрининга (Sentinel-2 / Copernicus LWQ).")
            actions.append("Провести гидрохимический экспресс-замер растворенного кислорода и pH на контрольных станциях.")
        else:
            alert_level = "GREEN"
            reasons.append(
                f"Показатели качества воды в пределах фоновой нормы (Chl-a = {predicted_chl_a:.1f} мкг/л, статус: {trophic_class})."
            )
            actions.append("Продолжить плановый фоновый спутниковый и гидрометеорологический мониторинг.")

        # 3. Добавление триплетов в граф знаний
        wb_uri = URIRef(BYWATER[water_body_id])
        wb_type_uri = BYWATER.Reservoir if is_reservoir else BYWATER.Lake
        self.graph.add((wb_uri, RDF.type, wb_type_uri))
        self.graph.add((wb_uri, RDFS.label, Literal(water_body_name, lang="ru")))

        assess_id = f"Assessment_{water_body_id}_{date_str.replace('-', '')}"
        assess_uri = URIRef(BYWATER[assess_id])
        self.graph.add((assess_uri, RDF.type, BYWATER.EutrophicationAssessment))
        self.graph.add((assess_uri, BYWATER.forWaterBody, wb_uri))
        self.graph.add((assess_uri, BYWATER.hasPredictedChlA, Literal(predicted_chl_a, datatype=XSD.float)))
        self.graph.add((assess_uri, BYWATER.hasBloomProbability, Literal(bloom_probability, datatype=XSD.float)))
        self.graph.add((assess_uri, BYWATER.hasTrophicIndex, Literal(tsi, datatype=XSD.float)))

        alert_uri = URIRef(BYWATER[f"Alert_{assess_id}"])
        self.graph.add((alert_uri, RDF.type, BYWATER.EarlyWarningAlert))
        self.graph.add((alert_uri, BYWATER.alertLevel, Literal(alert_level, datatype=XSD.string)))
        self.graph.add((alert_uri, BYWATER.explanationReason, Literal(" | ".join(reasons), datatype=XSD.string)))
        self.graph.add((alert_uri, BYWATER.recommendedAction, Literal(" | ".join(actions), datatype=XSD.string)))

        return AlertVerdict(
            water_body_id=water_body_id,
            water_body_name=water_body_name,
            assessment_date=date_str,
            predicted_chl_a=predicted_chl_a,
            bloom_probability=bloom_probability,
            trophic_index=tsi,
            trophic_class=trophic_class,
            alert_level=alert_level,
            reasons=reasons,
            recommended_actions=actions,
        )

    def export_graph_turtle(self, output_file: Path) -> None:
        self.graph.serialize(destination=str(output_file), format="turtle")
        logger.info(f"RDF граф сохранен в {output_file} ({len(self.graph)} триплетов)")

    def query_active_alerts(self) -> List[Dict[str, Any]]:
        """Выполняет SPARQL-запрос для извлечения предупреждений."""
        query = """
        PREFIX bywater: <http://w3id.org/belarus/water-quality#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?wbName ?chlA ?bloomProb ?level ?action
        WHERE {
            ?assess a bywater:EutrophicationAssessment ;
                    bywater:forWaterBody ?wb ;
                    bywater:hasPredictedChlA ?chlA ;
                    bywater:hasBloomProbability ?bloomProb .
            ?wb rdfs:label ?wbName .
            ?alert a bywater:EarlyWarningAlert ;
                   bywater:alertLevel ?level ;
                   bywater:recommendedAction ?action .
        }
        """
        results = []
        for row in self.graph.query(query):
            results.append({
                "water_body": str(row.wbName),
                "predicted_chl_a": float(row.chlA),
                "bloom_prob": float(row.bloomProb),
                "alert_level": str(row.level),
                "actions": str(row.action).split(" | "),
            })
        return results


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    ont_path = current_dir / "ontology.ttl"
    engine = WaterKnowledgeGraphEngine(ont_path)

    # Тестовый прогон вывода для двух водоёмов в летний период (июль 2025)
    v1 = engine.evaluate_water_body(
        water_body_id="BY_RES_001",
        water_body_name="Заславское водохранилище (Минское море)",
        is_reservoir=True,
        date_str="2025-07-21",
        predicted_chl_a=34.5,
        bloom_probability=0.88,
        temp_mean_14d=22.4,
        calm_fraction_7d=0.55,
        current_chl_a=24.0,
    )
    print("\n--- ВЕРДИКТ: ЗАСЛАВСКОЕ ВОДОХРАНИЛИЩЕ ---")
    print(f"Статус: {v1.alert_level} | Трофический класс: {v1.trophic_class} (TSI={v1.trophic_index})")
    print("Причины:", v1.reasons)
    print("Действия:", v1.recommended_actions)

    v2 = engine.evaluate_water_body(
        water_body_id="BY_LAKE_001",
        water_body_name="Озеро Нарочь",
        is_reservoir=False,
        date_str="2025-07-21",
        predicted_chl_a=5.2,
        bloom_probability=0.03,
        temp_mean_14d=20.1,
        calm_fraction_7d=0.30,
        current_chl_a=4.8,
    )
    print("\n--- ВЕРДИКТ: ОЗЕРО НАРОЧЬ ---")
    print(f"Статус: {v2.alert_level} | Трофический класс: {v2.trophic_class} (TSI={v2.trophic_index})")
    print("Причины:", v2.reasons)
    print("Действия:", v2.recommended_actions)

    export_path = current_dir.parent.parent / "data" / "processed" / "knowledge_graph_snapshot.ttl"
    engine.export_graph_turtle(export_path)
