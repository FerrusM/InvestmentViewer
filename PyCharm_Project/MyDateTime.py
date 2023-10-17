import datetime


def getUtcDateTime() -> datetime.datetime:
    """Возвращает текущие дату и время в UTC."""
    tz: datetime.tzinfo = datetime.timezone.utc
    return datetime.datetime.now(tz)


def getMoscowDateTime() -> datetime.datetime:
    """Возвращает текущие дату и время UTC+3."""
    tz: datetime.tzinfo = datetime.timezone(offset=datetime.timedelta(hours=3), name='МСК')
    return datetime.datetime.now(tz)


def getMicrosecondsCountFromDateTime(date_and_time: datetime.datetime) -> int:
    """Получает количество микросекунд со времён эпохи в datetime.datetime."""
    date_and_time_utc: datetime.datetime = date_and_time.replace(tzinfo=datetime.timezone.utc)  # Преобразуем в формат UTC.
    return date_and_time_utc.timestamp()*(10**6)


def ifDateTimeIsEmpty(date_and_time: datetime.datetime) -> bool:
    """Проверка datetime на наличие данных."""
    '''
    date_and_time_utc.timestamp() возвращает количество секунд с учётом микросекунд с начала эпохи.
    Это значение имеет тип float. Тип float не рекомендуется сравнивать с нулём,
    поэтому я вручную конвертирую секунды в микросекунды, чтобы получить тип int.
    '''
    return True if getMicrosecondsCountFromDateTime(date_and_time) == 0 else False


def ifTimeIsEmpty(entered_time: datetime.time) -> bool:
    """Является ли время пустым."""
    if entered_time.hour != 0 or entered_time.minute != 0 or entered_time.second != 0 or entered_time.microsecond != 0:
        return False
    else:
        return True


def reportDateIfOnlyDate(date_and_time: datetime.datetime) -> str:
    """Возвращает только дату, если все параметры времени равны нулям."""
    """
    Tinkoff API везде возвращает даты в формате datetime.datetime, но обычно эти даты не содержат время,
    поэтому я использую эту функцию для того, чтобы отображать эти даты без времени.
    Если вдруг Tinkoff API вернёт непустое время, оно будет отображено.
    """
    return date_and_time.strftime("%d.%m.%Y") if ifTimeIsEmpty(date_and_time.time()) else str(date_and_time)


def reportSignificantInfoFromDateTime(date_and_time: datetime.datetime):
    """Отображает дату и время, если есть время; если время нет, то отображает только дату; если нет ничего, то отображает "Нет данных"."""
    return "Нет данных" if ifDateTimeIsEmpty(date_and_time) else reportDateIfOnlyDate(date_and_time)
