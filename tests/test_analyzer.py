# tests/test_analyzer.py
import pytest
from steosmorphy import MorphAnalyzer

# Фикстура Pytest: создает один экземпляр анализатора для всех тестов в этом файле.


@pytest.fixture(scope="module")
def analyzer():
    """Инициализирует и возвращает экземпляр MorphAnalyzer."""
    print("\nИнициализация анализатора для тестов...")
    try:
        instance = MorphAnalyzer()
        print("Инициализация завершена.")
        return instance
    except Exception as e:
        pytest.fail(f"Не удалось инициализировать MorphAnalyzer: {e}")

# --- ТЕСТЫ ДЛЯ СЛОВАРНЫХ СЛОВ ---


@pytest.mark.parametrize("word, expected_lemma, expected_pos, expected_case, expected_forms", [
    # --- СУЩЕСТВИТЕЛЬНЫЕ ---
    ("мама", "мама", "Существительное", "Именительный", [
     "мама", "маме", "мамой", "мамою", "маму", "мамы"]),
    ("коту", "кот", "Существительное", "Дательный", [
     "кот", "кота", "коте", "котом", "коту", "коты", "котам", "котами", "котов"]),
    ("человек", "человек", "Существительное", "Именительный", [
     "человек", "человека", "люди", "людей", "людям"]),  # Проверка супплетивизма

    # --- ПРИЛАГАТЕЛЬНЫЕ и СУППЛЕТИВИЗМ ---
    ("хороший", "хороший", "Прилагательное", "Именительный",
     ["хороший", "хорошая", "лучший", "лучшая", "лучше"]),
    ("лучшая", "хороший", "Прилагательное", "Именительный",
     ["хороший", "хорошая", "лучший", "лучшая", "лучше"]),

    # --- ГЛАГОЛЫ ---
    ("идти", "идти", "Глагол", None, [
     "идти", "иду", "идёт", "шёл", "шла", "шли"]),
    ("шёл", "идти", "Глагол", None, [
     "идти", "иду", "идёт", "шёл", "шла", "шли"]),

    # --- МЕСТОИМЕНИЯ ---
    ("я", "я", "Местоимение", "Именительный",
     ["я", "меня", "мне", "мной", "мною"]),
    ("ему", "он", "Местоимение", "Дательный",
     ["его", "ей", "ему", "ею", "её", "им", "ими", "их", "ней", "них", "нём", "он", "она", "они", "оно"]),

    # --- ЧИСЛИТЕЛЬНЫЕ ---
    ("двум", "два", "Числительное", "Дательный",
     ["два", "две", "двух", "двум", "двумя"]),

    # --- НАРЕЧИЯ (неизменяемые) ---
    ("быстро", "быстро", "Наречие", None, ["быстро"]),

    # --- ПРИЧАСТИЯ ---
    ("сделавший", "сделать", "Причастие", "Именительный", [
     "сделавший", "сделавшего", "сделавшая", "сделавшую"]),

    # --- ДЕЕПРИЧАСТИЯ ---
    ("сделав", "сделать", "Деепричастие", None, ["сделав"]),

    # --- СЛУЖЕБНЫЕ ЧАСТИ РЕЧИ ---
    ("в", "в", "Предлог", None, ["в"]),
    ("и", "и", "Союз", None, ["и"]),
    ("не", "не", "Частица", None, ["не"]),
])
def test_analyze_dictionary_words(analyzer: MorphAnalyzer, word, expected_lemma, expected_pos, expected_case, expected_forms):
    """Тестирует разбор и генерацию форм для разных словарных слов."""
    result = analyzer.analyze(word)

    assert result is not None, f"Слово '{word}' не разобрано, хотя должно было"
    assert result.parses, f"Для слова '{word}' не найдено вариантов разбора"

    # Ищем нужный вариант разбора
    found_parse = None
    for p in result.parses:
        if p.lemma == expected_lemma and p.part_of_speech == expected_pos:
            found_parse = p
            break

    assert found_parse is not None, f"Ожидаемый разбор (лемма: {expected_lemma}, ЧР: {expected_pos}) не найден"

    if expected_case:
        assert found_parse.case == expected_case, f"Неверный падеж: ожидали '{expected_case}', получили '{found_parse.case}'"

    # Проверяем словоформы
    # Преобразуем в set для удобства сравнения
    actual_forms = {p.word for p in result.forms}
    for form in expected_forms:
        assert form in actual_forms, f"Ожидаемая словоформа '{form}' не найдена в сгенерированном списке"


def test_analyze_ambiguous_word(analyzer: MorphAnalyzer):
    """Тестирует разбор омонима 'стали'."""
    word = "стали"
    result = analyzer.analyze(word)

    assert len(
        result.parses) >= 2, f"Для слова '{word}' ожидалось как минимум 2 разбора, получено {len(result.parses)}"

    # Ищем разбор для глагола "стать"
    verb_parse = next((p for p in result.parses if p.lemma ==
                      "стать" and p.part_of_speech == "Глагол"), None)
    assert verb_parse is not None, "Не найден разбор для 'стали' как глагола"

    # Ищем разбор для существительного "сталь"
    noun_parse = next((p for p in result.parses if p.lemma ==
                      "сталь" and p.part_of_speech == "Существительное"), None)
    assert noun_parse is not None, "Не найден разбор для 'стали' как существительного"
    assert noun_parse.case == "Родительный"

# --- ТЕСТЫ ДЛЯ НЕСЛОВАРНЫХ СЛОВ (OOV) ---


@pytest.mark.parametrize("word, expected_lemma, expected_pos, expected_key_forms", [
    ("скилловым", "скилловый", "Прилагательное",
     ["скилловая", "скиллового", "скилловое", "скилловый", "скилловыми", "скилловых"]),
    ("чекал", "чекать", "Глагол", ["чекать", "чекает", "чекают"]),
    ("нейросетей", "нейросеть", "Существительное",
     ["нейросеть", "нейросети", "нейросетью", "нейросетям", "нейросетями", "нейросетях"]),
    ("пкауйкйцк", "пкауйкйцк", "Существительное",
     ["пкауйкйцк", "пкауйкйцка", "пкауйкйцками", "пкауйкйцках", "пкауйкйцку"]),

])
def test_analyze_oov_words(analyzer: MorphAnalyzer, word, expected_lemma, expected_pos, expected_key_forms):
    """Тестирует предсказание для несловарных слов."""
    result = analyzer.analyze(word)

    assert result is not None, f"Слово '{word}' не было предсказано, хотя должно было"
    assert len(
        result.parses) == 1, f"Для предсказанного слова ожидается 1 вариант разбора, получено {len(result.parses)}"

    p = result.first
    assert p.lemma == expected_lemma, f"Неверная предсказанная лемма: ожидали '{expected_lemma}', получили '{p.lemma}'"
    assert p.part_of_speech == expected_pos, f"Неверная предсказанная ЧР: ожидали '{expected_pos}', получили '{p.part_of_speech}'"

    # Проверяем наличие ключевых словоформ
    actual_forms = {f.word for f in result.forms}
    for form in expected_key_forms:
        assert form in actual_forms, f"Ожидаемая словоформа '{form}' не найдена в сгенерированном списке"


def test_parse_list(analyzer: MorphAnalyzer):
    """Тестирует корректность работы пакетного метода parse_list."""
    words = ["мама", "стали", "коту", "нейросети", "сёрчив"]

    expected_lemmas = {"мама", "стать", "сталь", "кот", "нейросеть", "сёрчить"}

    results = analyzer.parse_list(words)

    assert len(results) >= len(
        words), "Количество результатов должно быть >= количеству слов"

    found_lemmas = {p.lemma for p in results}

    assert found_lemmas == expected_lemmas, "Набор лемм в пакетной обработке не совпал с ожидаемым"

    # Проверяем, что результат отсортирован по слову
    word_list = [p.word for p in results]
    assert word_list == sorted(
        word_list), "Результат parse_list должен быть отсортирован"


def test_inflect_list(analyzer: MorphAnalyzer):
    """Тестирует корректность работы пакетного метода inflect_list."""
    words = ["мама", "бежать", "нейросети", "лучший"]

    expected_forms = {"мам",
                      "мама",
                      "мамам",
                      "мамах",
                      "мамой",
                      "бегут",
                      "бегущий",
                      "бежав",
                      "бежавший",
                      "бежим",
                      "нейросетей",
                      "нейросети",
                      "нейросеть",
                      "нейросетям",
                      "нейросетях",
                      "лучшую",
                      "хороших",
                      "наилучшая",
                      "наилучшие",
                      "наилучший", }

    forms = analyzer.inflect_list(words)

    # Проверяем наличие ключевых словоформ
    actual_forms = {f.word for f in forms}
    for form in expected_forms:
        assert form in actual_forms, f"Ожидаемая словоформа '{form}' не найдена в сгенерированном списке"
