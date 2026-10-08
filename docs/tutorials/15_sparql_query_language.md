# Обучающее руководство №15. Язык запросов к графам знаний SPARQL

> **Курс:** Интеллектуальная система мониторинга водных объектов Беларуси  
> **Уровень:** От базового Python к инженерной разработке  
> **Ключевые концепции:** SPARQL, сопоставление с шаблоном графа (Graph Pattern Matching), переменные `?var`, фильтры `FILTER`, выполнение запросов в `rdflib`  

---

## 1. Что такое SPARQL и почему обычный SQL здесь не работает?

В реляционных базах данных (PostgreSQL, MySQL) все данные лежат в жестких двумерных таблицах со строками и колонками. Чтобы достать данные, вы пишете SQL:
```sql
-- SQL: поиск в фиксированной таблице
SELECT lake_name, chl_a FROM water_assessments WHERE chl_a > 25.0;
```

Но в **Графе знаний** нет фиксированных таблиц и колонок! Там есть гигантская свободная сеть узлов и связей-триплетов.  
Для графов Консорциум Всемирной паутины (W3C) разработал специальный язык запросов — **SPARQL (SPARQL Protocol and RDF Query Language)**.

---

## 2. Главная идея SPARQL: Сопоставление с шаблоном (Graph Pattern Matching)

В SQL вы запрашиваете колонки. В SPARQL вы рисуете **«трафарет» (шаблон подграфа)** с неизвестными переменными.  
Любая неизвестная переменная обозначается **знаком вопроса** перед именем (например, `?lake`, `?chlA`, `?riskLevel`).

Движок SPARQL прикладывает этот трафарет ко всему графу знаний и мгновенно находит все места, которые совпадают по форме!

### Пример трафарета:
* *«Найди мне любой субъект `?assess`, который связан свойством `hasPredictedChlA` со значением `?chlA`, и найди связанное с ним озеро `?wb`, у которого название `?wbName`».*

---

## 3. Анатомия SPARQL-запроса

Запрос строится из четырёх основных блоков:

```sparql
# 1. Объявление префиксов (сокращений)
PREFIX bywater: <http://w3id.org/belarus/water-quality#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

# 2. Список переменных, которые мы хотим получить на выходе
SELECT ?wbName ?chlA ?riskLevel

# 3. Графовый трафарет триплетов
WHERE {
    ?assess a bywater:EutrophicationAssessment ;
            bywater:forWaterBody ?wb ;
            bywater:hasPredictedChlA ?chlA .
    
    ?wb rdfs:label ?wbName .

    ?alert bywater:alertLevel ?riskLevel .

    # 4. Условие фильтрации (как в SQL WHERE)
    FILTER(?chlA >= 25.0)
}
```

---

## 4. Выполнение SPARQL-запросов в Python через `rdflib`

Выполнять SPARQL-запросы можно прямо в Python без внешних баз данных, используя метод `graph.query()`:

```python
from rdflib import Graph

# 1. Загружаем сохраненный снимок графа знаний
g = Graph()
g.parse("water_eutrophication/data/processed/knowledge_graph_snapshot.ttl", format="turtle")

# 2. Описываем SPARQL-запрос:
query = """
PREFIX bywater: <http://w3id.org/belarus/water-quality#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?wbName ?chlA ?level ?action
WHERE {
    ?assess a bywater:EutrophicationAssessment ;
            bywater:forWaterBody ?wb ;
            bywater:hasPredictedChlA ?chlA .
    ?wb rdfs:label ?wbName .
    ?alert a bywater:EarlyWarningAlert ;
           bywater:alertLevel ?level ;
           bywater:recommendedAction ?action .
}
"""

# 3. Выполняем запрос:
results = g.query(query)

# 4. Печатаем извлеченные факты:
for row in results:
    print(f"Водоём: {row.wbName}")
    print(f"  Прогноз Chl-a: {float(row.chlA):.2f} мкг/л")
    print(f"  Статус тревоги: {row.level}")
    print(f"  Действия: {row.action}\n")
```

---

## 5. Как это реализовано в НАШЕМ курсовом проекте?

В файле `water_eutrophication/src/knowledge_graph/graph_engine.py` метод `query_active_alerts()` использует именно этот SPARQL-запрос, чтобы извлечь из графа знаний список всех предупреждений и передать их в веб-дашборд и REST API.

---

## 6. Рекомендованные прямые видеоуроки на YouTube

1. 🎬 **[Dr. Noureddin Sadawi: "SPARQL Tutorial — Part 1: Introduction and Basic Queries"](https://www.youtube.com/watch?v=FvmsQZ_6w24)**  
   *Самый знаменитый плейлист по SPARQL на YouTube: базовый синтаксис SELECT, WHERE, переменные ?x.*
2. 🎬 **[FIZ Karlsruhe: "Knowledge Graphs — SPARQL Graph Pattern Matching"](https://www.youtube.com/watch?v=kYJ4X8sJ-aE)**  
   *Академическая лекция о том, как устроен алгоритм сопоставления шаблонов графа под капотом.*
3. 🎬 **[W3C SPARQL 1.1 Query Language Documentation](https://www.w3.org/TR/sparql11-query/)**  
   *Официальная спецификация W3C с примерами сложных запросов, агрегаций (COUNT, AVG) и фильтров.*
