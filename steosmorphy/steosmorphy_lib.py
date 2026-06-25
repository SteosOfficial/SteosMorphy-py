# steosmorphy_lib.py
import ctypes
import json
import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import zstandard as zstd
from tqdm import tqdm
from typing import Optional


class _AnalyzerConfigC(ctypes.Structure):
    """Зеркало C-структуры AnalyzerConfig_C из cgo preamble (main.go)."""
    _fields_ = [
        ("capacity", ctypes.c_uint32),
        ("num_shards", ctypes.c_uint32),
    ]

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


@dataclass
class ShardConfig:
    total_capacity: int
    num_shards: int

    def __post_init__(self):
        if self.total_capacity == 0:
            return
        if self.total_capacity < 0:
            raise ValueError(f"shard size must be >= 0, got {self.total_capacity}")
        if self.num_shards < 1 or (self.num_shards & (self.num_shards - 1) != 0) or self.total_capacity < self.num_shards:
            raise ValueError(f"num_shards must be greater than 0 and less than shard_size, got: {self.num_shards}")


@dataclass
class AnalyzerConfig:
    cache: Optional[ShardConfig] = None

    def __post_init__(self):
        if self.cache is None:
            self.cache = ShardConfig(total_capacity=0, num_shards=0)

    def to_c_struct(self) -> _AnalyzerConfigC:
        total_capacity = self.cache.total_capacity
        num_shards = self.cache.num_shards
        return _AnalyzerConfigC(capacity=total_capacity, num_shards=num_shards)


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

    def __init__(self, config: AnalyzerConfig) -> None:
        if self._initialized:
            return
        self._config = config
        self._load_library()
        self._initialized = True

    def _load_library(self):
        # Определяем имя библиотеки в зависимости от ОС
        import platform
        system = platform.system()
        if system == 'Windows':
            lib_name = 'steosmorphy.dll'
        elif system == 'Linux':
            lib_name = 'steosmorphy.so'
        elif system == 'Darwin':
            lib_name = 'steosmorphy.dylib'
        else:
            raise RuntimeError(f"Unsupported OS: {system}")

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

            self.lib.Init.argtypes = [ctypes.c_char_p, _AnalyzerConfigC]
            self.lib.Init.restype = ctypes.c_void_p

            self.lib.AnalyzeJson.argtypes = [ctypes.c_char_p]
            self.lib.AnalyzeJson.restype = ctypes.c_void_p

            self.lib.ParseListJson.argtypes = [ctypes.c_char_p]
            self.lib.ParseListJson.restype = ctypes.c_void_p

            self.lib.InflectListJson.argtypes = [ctypes.c_char_p]
            self.lib.InflectListJson.restype = ctypes.c_void_p

            self.lib.FreeCString.argtypes = [ctypes.c_void_p]
            self.lib.FreeCString.restype = None

            self.lib.ResizeShard.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            self.lib.ResizeShard.restype = ctypes.c_void_p

            self.lib.Delete.argtypes = []
            self.lib.Delete.restype = None

            config_c = self._config.to_c_struct()

            self.lib.Init(
                str(uncompressed_dict_path).encode('utf-8'),
                config_c
            )

    def apply_config(self, config: AnalyzerConfig) -> None:
        """Выполняет модификацию конфигурации анализатора"""
        def resize_cache(total_capacity: int, num_shards: int) -> None:
            err_ptr = self.lib.ResizeShard(
                ctypes.c_uint32(total_capacity), ctypes.c_uint32(num_shards)
            )
            if err_ptr:
                err_msg = ctypes.cast(err_ptr, ctypes.c_char_p).value.decode('utf-8')
                self.lib.FreeCString(err_ptr)
                raise RuntimeError(f"ResizeShard failed: {err_msg}")

        resize_cache(config.cache.total_capacity, config.cache.num_shards)

    def destroy(self) -> None:
        """Явно уничтожает синглтон: сбрасывает Go-side globalAnalyzer и Python-обёртку."""
        if hasattr(self, 'lib'):
            self.lib.Delete()
            del self.lib
        self._initialized = False
        MorphAnalyzer._instance = None

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
        parses = raw_data.get('parses', [])
        if parses is None:
            parses = []
        parses_list = [Parsed(p_dict) for p_dict in parses]

        # Преобразуем словари из 'forms' в объекты Parsed
        forms = raw_data.get('forms', [])
        if forms is None:
            forms = []
        forms_list = [Parsed(f_dict) for f_dict in forms]

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
