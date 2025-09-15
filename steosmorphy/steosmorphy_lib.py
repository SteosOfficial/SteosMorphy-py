# steosmorphy_lib.py
import ctypes
import json
import os
import platform
from importlib import resources
from pathlib import Path
import zstandard as zstd  
from tqdm import tqdm  

# Вспомогательная функция для получения пути к кэшу


def get_cache_dir() -> Path:
    cache_dir = Path(os.getenv("STEOSMORPHY_CACHE_DIR",
                               Path.home() / ".steosmorphy"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


class Parsed:
    """
    Объект, представляющий один полный морфологический разбор слова.
    Атрибуты напрямую соответствуют полям JSON, получаемого от Go.
    """

    def __init__(self, data: dict):
        self.word: str = data.get('word')
        self.tags: str = data.get('tags')
        self.lemma: str = data.get('lemma')
        self.part_of_speech: str = data.get('part_of_speech')
        self.animacy: str = data.get('animacy')
        self.aspect: str = data.get('aspect')
        self.case: str = data.get('case')
        self.gender: str = data.get('gender')
        self.involvement: str = data.get('involvement')
        self.mood: str = data.get('mood')
        self.number: str = data.get('number')
        self.person: str = data.get('person')
        self.tense: str = data.get('tense')
        self.transitivity: str = data.get('transitivity')
        self.voice: str = data.get('voice')
        # Преобразуем список "прочих" тегов в set для удобства
        self.other_tags: set = set(data.get('other_tags', {}).keys())

    def __repr__(self) -> str:
        """Удобное представление объекта для отладки."""
        return (f"Parsed(word='{self.word}', lemma='{self.lemma}', "
                f"POS='{self.part_of_speech}', tags='{self.tags}')")


class AnalysisResult:
    """
    Контейнер для полного результата анализа слова, включая
    варианты разбора и все возможные словоформы.
    """

    def __init__(self, parses: list[Parsed], forms: list[Parsed]):
        self.parses = parses
        self.forms = forms
        # Для удобства, делаем самый вероятный разбор доступным напрямую
        self.first = parses[0] if parses else None

    def __repr__(self) -> str:
        return f"<AnalysisResult: {len(self.parses)} parses, {len(self.forms)} forms>"


class MorphAnalyzer:
    """
    Python-обертка для высокопроизводительного морфологического анализатора,
    написанного на Go.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MorphAnalyzer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        system = platform.system()
        if system == 'Windows':
            lib_name = 'steosmorphy.dll'
        elif system == 'Linux':
            lib_name = 'steosmorphy.so'
        elif system == 'Darwin':
            lib_name = 'steosmorphy.dylib'
        else:
            raise RuntimeError(f"Неподдерживаемая ОС: {system}")

        cache_dir = get_cache_dir()
        uncompressed_dict_path = cache_dir / "morph.dawg"

        # Проверяем, есть ли уже распакованный словарь в кэше
        if not uncompressed_dict_path.exists():
            print(
                f"Распаковка словаря в {cache_dir} (это займет несколько секунд)...")

            # 2. Если нет, находим сжатый словарь внутри пакета
            with resources.path('steosmorphy', 'morph.dawg.zst') as compressed_path:
                # 3. Распаковываем его в кэш с прогресс-баром
                self._decompress_file(compressed_path, uncompressed_dict_path)

            print("Словарь успешно распакован.")

        with resources.path('steosmorphy', lib_name) as lib_path:

            self.lib = ctypes.CDLL(str(lib_path))
            self.lib.Init.argtypes = [ctypes.c_char_p]
            self.lib.Init.restype = ctypes.c_void_p
            self.lib.Init.restype = ctypes.c_int
            self.lib.Init.restype = None
            self.lib.AnalyzeJson.argtypes = [ctypes.c_char_p]
            # Важно: restype должен быть void_p, так как мы получаем указатель
            self.lib.AnalyzeJson.restype = ctypes.c_void_p
            self.lib.ParseListJson.argtypes = [ctypes.c_char_p]
            self.lib.ParseListJson.restype = ctypes.c_void_p
            self.lib.InflectListJson.argtypes = [ctypes.c_char_p]
            self.lib.InflectListJson.restype = ctypes.c_void_p
            self.lib.FreeCString.argtypes = [ctypes.c_void_p]
            self.lib.FreeCString.restype = None

            self.lib.Init(str(uncompressed_dict_path).encode('utf-8'))

        self._initialized = True

    def _decompress_file(self, compressed_path: Path, target_path: Path):
        """Распаковывает файл .zst с прогресс-баром."""
        dctx = zstd.ZstdDecompressor()
        total_size = compressed_path.stat().st_size

        with open(compressed_path, 'rb') as in_f, open(target_path, 'wb') as out_f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Распаковка") as pbar:
                def updater(chunk):
                    pbar.update(len(chunk))
                    return chunk

                reader = dctx.stream_reader(in_f)

                # Читаем по частям, чтобы отображать прогресс
                while True:
                    chunk = reader.read(16384)  # 16KB
                    if not chunk:
                        break
                    out_f.write(chunk)
                    pbar.update(len(chunk))

    def analyze(self, word: str) -> AnalysisResult:
        """
        Выполняет полный морфологический анализ слова.

        :param word: Слово для анализа.
        :return: Объект AnalysisResult, содержащий списки объектов Parsed.
        """
        word_bytes = word.encode('utf-8')
        # Получаем указатель на C-строку (JSON)
        json_ptr = self.lib.AnalyzeJson(word_bytes)

        # Преобразуем указатель в Python-строку
        json_string = ctypes.cast(
            json_ptr, ctypes.c_char_p).value.decode('utf-8')

        # Освобождаем память, выделенную Go
        self.lib.FreeCString(json_ptr)

        # Парсим JSON в стандартный Python dict
        raw_data = json.loads(json_string)

        # Преобразуем словари из 'parses' в объекты Parsed
        parses_list = [Parsed(p_dict) for p_dict in raw_data.get('parses', [])]

        # Преобразуем словари из 'forms' в объекты Parsed
        forms_list = [Parsed(f_dict) for f_dict in raw_data.get('forms', [])]

        # Возвращаем единый объект-контейнер
        return AnalysisResult(parses=parses_list, forms=forms_list)

    def parse_list(self, words: list[str]) -> list[Parsed]:
        """
        Анализирует список слов в пакетном режиме для максимальной производительности.
        Возвращает плоский список всех возможных разборов для всех слов.

        :param words: Список строк для анализа.
        :return: Список объектов Parsed.
        """
        if not words:
            return []

        # 1. Сериализуем список слов в JSON
        words_json = json.dumps(words)

        # 2. Вызываем Go-функцию
        result_ptr = self.lib.ParseListJson(words_json.encode('utf-8'))

        # 3. Получаем и освобождаем результат
        result_json = ctypes.cast(
            result_ptr, ctypes.c_char_p).value.decode('utf-8')
        self.lib.FreeCString(result_ptr)

        # 4. Десериализуем JSON и создаем объекты Parsed
        raw_data = json.loads(result_json)

        # Проверяем на возможную ошибку от Go
        if isinstance(raw_data, list) and len(raw_data) > 0 and 'error' in raw_data[0]:
            raise RuntimeError(
                f"Ошибка в Go-библиотеке: {raw_data[0]['error']}")

        return [Parsed(p_dict) for p_dict in raw_data]

    def inflect_list(self, words: list[str]) -> list[Parsed]:
        """
        Анализирует список слов в пакетном режиме для максимальной производительности.
        Возвращает плоский список всех возможных разборов для всех слов.

        :param words: Список строк для анализа.
        :return: Список объектов Parsed.
        """
        if not words:
            return []

        # 1. Сериализуем список слов в JSON
        words_json = json.dumps(words)

        # 2. Вызываем Go-функцию
        result_ptr = self.lib.InflectListJson(words_json.encode('utf-8'))

        # 3. Получаем и освобождаем результат
        result_json = ctypes.cast(
            result_ptr, ctypes.c_char_p).value.decode('utf-8')
        self.lib.FreeCString(result_ptr)

        # 4. Десериализуем JSON и создаем объекты Parsed
        raw_data = json.loads(result_json)

        # Проверяем на возможную ошибку от Go
        if isinstance(raw_data, list) and len(raw_data) > 0 and 'error' in raw_data[0]:
            raise RuntimeError(
                f"Ошибка в Go-библиотеке: {raw_data[0]['error']}")

        return [Parsed(p_dict) for p_dict in raw_data]
