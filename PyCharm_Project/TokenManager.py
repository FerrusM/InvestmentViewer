from PyQt6.QtCore import QSettings


class TokenManager:
    """Класс для управления токенами доступа."""
    def __init__(self):
        self.file_name: str = 'tokens'  # Имя файла.
        self.prefix: str = 'tokens'  # Префикс.
        self.key: str = 'token'  # Ключ.

        # Указываем расположение и формат (ini-файл) сохранения настроек.
        self.settings = QSettings(self.file_name, QSettings.Format.IniFormat)

        self._tokens_list: list[str] = self._extractTokens()  # Извлекаем список токенов из ini-файла.

    def _extractTokens(self) -> list[str]:
        """Извлекает токены из ini-файла."""
        size: int = self.settings.beginReadArray(self.prefix)  # Количество элементов в массиве.
        tokens_list: list[str] = []
        for i in range(size):
            self.settings.setArrayIndex(i)  # Устанавливает текущий индекс массива в i.
            tokens_list.append(self.settings.value(self.key))
        self.settings.endArray()
        return tokens_list

        # size: int = self.settings.beginReadArray(self.prefix)  # Количество элементов в массиве.
        # tokens_list: list[str] = self.settings.value('{0}/{1}'.format(self.prefix, self.key), [])
        # self.settings.endArray()
        # return tokens_list

    def addToken(self, new_token: str):
        """Добавляет токен."""
        # token_index: int = len(self._tokens_list)
        self._tokens_list.append(new_token)
        # self.settings.beginWriteArray(self.prefix)  # Добавляет префикс в текущую группу и начинает запись массива.
        # self.settings.setArrayIndex(token_index)  # Устанавливает текущий индекс массива в i.
        # self.settings.setValue(self.key, new_token)
        # self.settings.endArray()

        self._saveTokens()  # Перезаписывает массив токенов в ini-файле.

    def deleteToken(self, token_index: int) -> str:
        """Удаляет токен."""
        # self.settings.beginReadArray(self.prefix)  # Добавляет префикс в текущую группу и начинает запись массива.
        # self.settings.setArrayIndex(token_index)  # Устанавливает текущий индекс массива в i.
        # self.settings.remove(self.key)
        # self.settings.endArray()
        # return self._tokens_list.pop(token_index)

        deleted_token: str = self._tokens_list.pop(token_index)
        self.settings.remove(self.prefix)
        self._saveTokens()  # Перезаписывает массив токенов в ini-файле.
        return deleted_token

    def _saveTokens(self):
        """Сохраняет все токены в ini-файл."""
        self.settings.beginWriteArray(self.prefix)  # Добавляет префикс в текущую группу и начинает запись массива.
        for i, token in enumerate(self._tokens_list):
            self.settings.setArrayIndex(i)  # Устанавливает текущий индекс массива в i.
            self.settings.setValue(self.key, token)
        self.settings.endArray()

    def getTokens(self) -> list[str]:
        """Возвращает список токенов."""
        return self._tokens_list
