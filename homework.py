import logging
import os
import sys
import time

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
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def send_message(bot, message):
    """Отправка сообщения ботом."""
    chat_id = TELEGRAM_CHAT_ID
    text = message
    try:
        bot.send_message(chat_id, text)
        logging.debug('Сообщение успешно отправлено')
        bot.send_message(chat_id, 'Успешно отправлено')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        ).json()
        if requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        ).status_code != 200:
            logging.error('недоступность эндпоинта '
                          'https://practicum.yandex.ru/api/user_api/'
                          'homework_statuses/')
            raise Exception
    except requests.RequestException as error:
        logging.error(error)
    return response


def check_response(response):
    """Проверка ответа на корректность."""
    if response is None:
        logging.error('Ответ пуст')
        raise Exception
    if not isinstance(response, dict):
        logging.error('Ответ не содержит словаря')
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        logging.error('В ответе нет списка домашек')
        raise TypeError


def parse_status(homework):
    """Получение статуса проверки работы."""
    if homework.get('status') is None:
        logging.error('Статус не обнаружен')
        raise KeyError('Статус не обнаружен')
    if homework.get('status') not in HOMEWORK_VERDICTS:
        logging.error('Ожидаемые ключи статуса отсутствуют')
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
        logging.critical('Не все переменные окружения на месте')
        sys.exit('Не удалось найти токен')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    response = {}

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks_length = len(response.get('homeworks'))
            for i in range(0, homeworks_length):
                message = parse_status(response.get('homeworks')[i])
                send_message(bot, message)

        except Exception as error:
            logging.error(f'Ошибка при запросе к API: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            if response.get('current_date') is not None:
                timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
