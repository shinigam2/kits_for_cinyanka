# Обучающее руководство №14. Программная работа с графами знаний в Python (библиотека rdflib)

> **Курс:** Интеллектуальная система мониторинга водных объектов Беларуси  
> **Уровень:** От базового Python к инженерной разработке  
> **Ключевые концепции:** `Graph`, `URIRef`, `Literal`, `Namespace`, добавление триплетов, привязка префиксов (`bind`), сериализация в Turtle  

---

## 1. Зачем нужна библиотека `rdflib`?

В руководстве №13 мы изучили теоретическую модель графа (триплеты Субъект—Предикат—Объект) и формат Turtle (`.ttl`).  
Но как создавать эти триплеты программно на Python в режиме реального времени?

Когда модель машинного обучения выдаёт прогноз:
```python
predicted_chl_a = 32.31
bloom_prob = 0.967
```
Мы не можем вручную открывать текстовый редактор и вписывать эти числа в `.ttl`. Нам нужен программный интерфейс, который создаст узлы графа в памяти и свяжет их логическими дугами.

**`rdflib`** — это общепризнанная в мире Python-библиотека для работы с графами знаний (аналог Pandas, но для триплетов).

---

## 2. Четыре главных строительных блока `rdflib`

```python
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD
```

### 1. `Graph` (Хранилище графа)
Контейнер в оперативной памяти, в котором живут все узлы и связи.

### 2. `URIRef` (Узел-Сущность)
Уникальный идентификатор сущности (веб-ссылка). Это может быть озеро, класс или свойство:
```python
lake_uri = URIRef("http://w3id.org/belarus/water-quality#BY_RES_001")
```

### 3. `Literal` (Узел-Значение)
Примитивное значение: число, строка, дата. Может содержать язык (`lang="ru"`) или строгий тип данных (`datatype=XSD.float`):
```python
name = Literal("Заславское водохранилище", lang="ru")
chl_value = Literal(32.31, datatype=XSD.float)
```

### 4. `Namespace` (Фабрика префиксов)
Чтобы не писать длинные адреса вручную, мы создаём пространство имён:
```python
BYWATER = Namespace("http://w3id.org/belarus/water-quality#")

# Теперь через точку или квадратные скобки можно создавать любые URI:
lake = BYWATER.BY_RES_001      # эквивалентно http://w3id.org/belarus/water-quality#BY_RES_001
is_reservoir = BYWATER.Reservoir
```

---

## 3. Как строить граф в коде: пошаговый пример

```python
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS
from rdflib.namespace import XSD

# 1. Создаем пустой граф
g = Graph()

# 2. Объявляем префикс для нашего проекта
BYWATER = Namespace("http://w3id.org/belarus/water-quality#")
g.bind("bywater", BYWATER)  # Регистрируем префикс для красивого сохранения в Turtle

# 3. Создаем сущность озера и задаем ей свойства:
lake = URIRef(BYWATER["BY_RES_001"])

# Добавляем триплет 1: озеро является типом Reservoir
g.add((lake, RDF.type, BYWATER.Reservoir))

# Добавляем триплет 2: русское название озера
g.add((lake, RDFS.label, Literal("Заславское водохранилище (Минское море)", lang="ru")))

# Добавляем триплет 3: прогноз хлорофилла-a
g.add((lake, BYWATER.hasPredictedChlA, Literal(32.31, datatype=XSD.float)))

# 4. Сохраняем граф в файл Turtle на диск:
g.serialize(destination="my_lake_graph.ttl", format="turtle")
print(f"Граф успешно сохранен! Всего триплетов в памяти: {len(g)}")
```

---

## 4. Как это реализовано в НАШЕМ курсовом проекте?

В файле `water_eutrophication/src/knowledge_graph/graph_engine.py` класс `WaterKnowledgeGraphEngine` делает ровно это для каждого нового прогноза:

```python
# Создаем уникальный узел факта оценки: Assessment_BY_RES_001_20250721
assess_id = f"Assessment_{water_body_id}_{date_str.replace('-', '')}"
assess_uri = URIRef(BYWATER[assess_id])

# Связываем оценку с водоемом:
self.graph.add((assess_uri, RDF.type, BYWATER.EutrophicationAssessment))
self.graph.add((assess_uri, BYWATER.forWaterBody, wb_uri))

# Записываем прогнозные факты:
self.graph.add((assess_uri, BYWATER.hasPredictedChlA, Literal(predicted_chl_a, datatype=XSD.float)))
self.graph.add((assess_uri, BYWATER.hasBloomProbability, Literal(bloom_probability, datatype=XSD.float)))

# Записываем сгенерированный алерт тревоги:
self.graph.add((alert_uri, BYWATER.alertLevel, Literal(alert_level, datatype=XSD.string)))
self.graph.add((alert_uri, BYWATER.recommendedAction, Literal(" | ".join(actions), datatype=XSD.string)))
```
В результате при каждом прогнозе формируется семантический снимок `knowledge_graph_snapshot.ttl`, содержащий все факты и связи!

---

## 5. Рекомендованные прямые видеоуроки на YouTube

1. 🎬 **[Knowledge Graphs with RDFLib in Python (Hands-On Tutorial)](https://www.youtube.com/watch?v=F529qQZ2G2k)**  
   *Пошаговый урок: установка rdflib, создание графа, узлы Literal и URIRef, экспорт в Turtle.*
2. 🎬 **[IBM Technology: "How to Build a Knowledge Graph"](https://www.youtube.com/watch?v=kYJ4X8sJ-aE)**  
   *Практический разбор архитектуры: как соединять программный код на Python с графовыми хранилищами.*
3. 🎬 **[Official RDFLib Documentation](https://rdflib.readthedocs.io/)**  
   *Лучший вводный интерактивный Quickstart на официальном сайте библиотеки.*
