import logging
import os
import sys
import time
import json

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    stream=sys.stdout)
logger = logging.getLogger(__name__)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия всех необходимых токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def send_message(bot, message):
    """Отправка сообщения ботом."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно отправлено')
    except telegram.TelegramError as error:
        logger.error(f'Ошибка отправки на стороне Telegram: {error}')
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        response_raw = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except requests.RequestException as error:
        logger.error(f'Ошибка выполнения запроса: {error}')
        raise Exception('Ошибка выполнения запроса')

    if response_raw.status_code != 200:
        logger.error('недоступность эндпоинта '
                     'https://practicum.yandex.ru/api/user_api/'
                     'homework_statuses/')
        raise Exception('Нет доступа к эндпоинту')

    try:
        response = response_raw.json()
    except json.decoder.JSONDecodeError as error:
        logger.error(f'Ошибка декодера JSON: {error}')
        raise Exception('Ошибка декодера JSON')
    return response


def check_response(response):
    """Проверка ответа на корректность."""
    if response is None:
        logger.error('Ответ пуст')
        raise Exception('Ответ пуст')
    if not isinstance(response, dict):
        logger.error('Ответ не содержит словаря')
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        logger.error('В ответе нет списка домашек')
        raise TypeError
    if not isinstance(response.get('current_date'), int):
        logger.error('В ответе нет UNIX-метки')
        raise TypeError


def parse_status(homework):
    """Получение статуса проверки работы."""
    if homework.get('status') is None:
        logger.error('Статус не обнаружен')
        raise KeyError('Статус не обнаружен')
    if homework.get('status') not in HOMEWORK_VERDICTS:
        logger.error('Ожидаемые ключи статуса отсутствуют')
        raise KeyError('Ошибка')
    if not homework.get('homework_name'):
        raise KeyError('Не найден ключ')
    if homework is not None:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        return (f'Изменился статус проверки работы "{homework_name}". '
                f'{HOMEWORK_VERDICTS[homework_status]}')
    else:
        return 'Ошибка при получении статуса проверки домашки'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Не все переменные окружения на месте')
        sys.exit('Не удалось найти токен')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    response = {}

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            for hometask in response.get('homeworks'):
                message = parse_status(hometask)
                send_message(bot, message)

        except Exception as error:
            logger.error(f'Ошибка при запросе к API: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            if response.get('current_date') is not None:
                timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
