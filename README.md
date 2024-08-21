# Детектор дефектов в аудио телеграм бот
## Roadmap
* Детектор дефектов
  1. **Преобразование аудио в текст, получение временных меток предложений**: _Google Cloud Speech-to-Text_ `google-cloud-speech`
  2. **Сравнение транскрибированного и исходного текста**: `difflib`
  3. **Определение времени отсутствующих частей**
* Телеграм бот - две составляющие (Frontend, Backend), взаимодействие через REST api
  1. **Backend**: `aiohttp`
  2. **Frontend**: `python-telegram-bot`, `aiohttp`

## Структура проекта
* audio_defect_detector.py - функцию транскрибации и поиска потеряшек
* backend.py - backend сервис обработки аудио
* bot.py - UI телеграм бот
* config.py - конфигурация бота
* /input_examples - примеры аудио и текста для тестирования
* audio_defect_detector.ipynb - ноутбук для экспериментирования

## Ограничения
* WAV/AIFF/FLAC аудио файлы менее 60 секунд или размер меньше 10 MB

## Дальнейшие улучшения
* Простейший прогресс бар с 4-мя состояниями - реализация через WebSocket
  * Отправка - 0%
  * Обработка - 25%
  * Поиск ошибок - 75%
  * Результат - 100%
* Потоковая обработка аудио