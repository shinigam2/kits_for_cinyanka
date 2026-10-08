# Обучающее руководство №4. Сбор данных через REST API и библиотека requests в Python

> **Курс:** Интеллектуальная система мониторинга водных объектов Беларуси  
> **Уровень:** От базового Python к инженерной разработке  
> **Ключевые концепции:** HTTP-протокол, REST API, метод GET, Query Parameters, статус-коды, JSON, обработка сбоев сети  

---

## 1. Что такое API и REST простыми словами?

Когда вы открываете сайт в браузере (например, `yandex.by` или `google.com`), сервер возвращает красивый HTML-код с кнопками, картинками и стилями, рассчитанный на просмотр человеком.

Но программам (нашим Python-скриптам) не нужны кнопки и картинки. Им нужны **чистые структурированные данные** (числа, даты, таблицы).

**API (Application Programming Interface)** — это «служебный вход» сайта для программ.  
**REST API** — общемировой стандарт того, как программы обмениваются данными по интернету через протокол HTTP:
* Вы (Клиент / Python-скрипт) отправляете HTTP-запрос по специальному адресу (URL-эндпоинту).
* Сервер (например, суперкомпьютер NASA) обрабатывает запрос и возвращает ответ в текстовом формате **JSON** (текстовое представление Python-словаря).

---

## 2. Анатомия HTTP-запроса

Любой GET-запрос к API состоит из трёх частей:

1. **Базовый URL (Base URL):** адрес сервиса.  
   Например: `https://power.larc.nasa.gov/api/temporal/daily/point`
2. **Параметры запроса (Query Parameters):** данные, которые идут после знака `?` через амперсанд `&`:  
   `?latitude=53.985&longitude=27.380&start=20200101&end=20251231`
3. **Статус-код ответа (HTTP Status Code):** 3-значное число, сообщающее результат:
   * **`200 OK`** — Успех! Сервер нашёл данные и прислал ответ.
   * **`400 Bad Request`** — Ошибка в запросе (например, вы передали широту `150°`, которой не бывает).
   * **`404 Not Found`** — Запрашиваемый адрес не существует.
   * **`500 Internal Server Error`** — Ошибка на самом сервере (сервер NASA «упал» или перегружен).

---

## 3. Библиотека `requests` в Python

`requests` — самая популярная библиотека Python в мире. Она делает отправку сетевых запросов элементарной.

### Установка:
```bash
.venv/bin/pip install requests
```

### Базовый пример отправки запроса:
```python
import requests

# Базовый адрес API
url = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Словарь параметров: библиотека requests сама преобразует его в формат URL!
params = {
    "parameters": "T2M,WS2M",
    "community": "AG",
    "latitude": 53.9850,
    "longitude": 27.3800,
    "start": "20250701",
    "end": "20250705",
    "format": "JSON"
}

# Отправляем GET-запрос с таймаутом 30 секунд (чтобы скрипт не завис навсегда при обрыве сети)
response = requests.get(url, params=params, timeout=30)

# Проверяем, что запрос успешен (вызовет исключение при кодах 4xx или 5xx)
response.raise_for_status()

# Превращаем ответ сервера в обычный словарь Python:
data = response.json()

print("Тип полученных данных:", type(data))  # <class 'dict'>
print("Ключи ответа:", list(data.keys()))
```

---

## 4. Как это реализовано в НАШЕМ курсовом проекте?

В файле `water_eutrophication/src/data/download_meteo.py` написана функция `fetch_nasa_power_daily`:

```python
def fetch_nasa_power_daily(lat: float, lon: float, start_date: str, end_date: str, parameters: list[str]):
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    # NASA POWER требует даты без дефисов: 2020-01-01 -> 20200101
    start_str = start_date.replace("-", "")
    end_str = end_date.replace("-", "")

    params = {
        "parameters": ",".join(parameters),  # "T2M,T2M_MAX,WS2M,PRECTOTCORR"
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": start_str,
        "end": end_str,
        "format": "JSON",
        "header": "true",
    }

    response = requests.get(base_url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()
```

### Парсинг вложенного ответа JSON:
NASA возвращает глубоко вложенный JSON вида:
```json
{
  "properties": {
    "parameter": {
      "T2M": {
        "20250701": 21.45,
        "20250702": 23.10
      }
    }
  }
}
```
В функции `parse_nasa_power_response()` мы проходим циклом по ключам дат и преобразуем этот JSON в красивую плоскую таблицу Pandas.

---

## 5. Где и как тренироваться делать API-запросы

Для практики работы с API не обязательно сразу опрашивать NASA. Есть отличные бесплатные открытые API:

1. **[Open-Meteo API (open-meteo.com)](https://open-meteo.com/)** — Бесплатное европейское погодное API без необходимости регистрации и ключей.  
   *Попробуйте запросить погоду для Минска: `https://api.open-meteo.com/v1/forecast?latitude=53.9&longitude=27.56&current_weather=true`*.
2. **[HTTPBin (httpbin.org)](https://httpbin.org/)** — Полигон для тестирования любых типов HTTP-запросов (`/get`, `/post`, проверка статус-кодов `/status/404`).
3. **[Postman](https://www.postman.com/)** или плагин **Thunder Client** в VS Code — программы с графическим интерфейсом для отправки и тестирования API-запросов перед написанием кода на Python.

---

## 6. Рекомендованные прямые видео и курсы

### Прямые ссылки на видеоуроки (YouTube):
1. 🎬 **[Corey Schafer: "Python Requests Tutorial: Request Web Pages, Read JSON, and More"](https://www.youtube.com/watch?v=tb8gHvYlCFs)**  
   *Абсолютный эталон: как отправлять GET-запросы, передавать параметры `params` и парсить JSON.*
2. 🎬 **[Fireship: "RESTful APIs in 100 Seconds"](https://www.youtube.com/watch?v=lsMQRaeKNDk)**  
   *Самое быстрое и понятное визуальное объяснение концепции REST API и методов HTTP.*
3. 🎬 **[Corey Schafer: "Python Tutorial: Working with JSON Data using the json Module"](https://www.youtube.com/watch?v=9N6a-VLBa2I)**  
   *Разбор функций `json.loads` и `json.dumps`: как превращать строки в словари Python.*
