# tests/test_benchmark.py
import pytest
import time
from steosmorphy import MorphAnalyzer, AnalyzerConfig

# --- Фикстура для подготовки данных ---


@pytest.fixture(scope="session")
def analyzer_instance():
    """
    Фикстура, которая создает ОДИН экземпляр анализатора для всей тестовой сессии.
    """
    print("\n[LOAD TEST] Инициализация анализатора...")
    return MorphAnalyzer(AnalyzerConfig())

# --- Нагрузочный тест  ---


@pytest.mark.parametrize(
    "num_iterations",
    [1000, 10_000, 100_000],
    ids=["1K_runs", "10K_runs", "100K_runs"]
)
def test_load_performance_sequential(analyzer_instance: MorphAnalyzer, num_iterations: int):
    """
    Проводит нагрузочное тестирование последовательного метода analyze.
    """
    print(f"\n--- Запуск нагрузочного теста на {num_iterations} итераций ---")

    analyzer = analyzer_instance

    start_time = time.perf_counter()

    for _ in range(num_iterations):
        analyzer.analyze("междисциплинарный")

    end_time = time.perf_counter()
    duration = end_time - start_time
    avg_time_per_word = duration / num_iterations

    ops_per_second = num_iterations / \
        duration if duration > 0 else float('inf')

    print(f"Итог для {num_iterations} итераций:")
    print(f"  Общее время: {duration:.4f} секунд")
    print(f"  Среднее время на слово: {avg_time_per_word * 1e6:.2f} мкс")
    print(f"  Производительность: {ops_per_second:,.2f} слов/сек")


@pytest.mark.parametrize(
    "num_words",
    [1000, 10_000, 100_000],
    ids=["1K_runs", "10K_runs", "100K_runs"]
)
def test_load_performance_parse_list(analyzer_instance: MorphAnalyzer, num_words: int):
    """
     Проводит нагрузочное тестирование пакетного метода parse_list.
     """
    print(
        f"\n--- Запуск нагрузочного теста на {num_words} слов ---")

    analyzer = analyzer_instance

    start_time = time.perf_counter()

    analyzer.parse_list(["слово"] * num_words)

    end_time = time.perf_counter()
    duration = end_time - start_time
    avg_time_per_word = duration / num_words

    ops_per_second = num_words / \
        duration if duration > 0 else float('inf')

    print(f"Итог для {num_words} слов:")
    print(f"  Общее время: {duration:.4f} секунд")
    print(f"  Среднее время на слово: {avg_time_per_word * 1e6:.2f} мкс")
    print(f"  Производительность: {ops_per_second:,.2f} слов/сек")


@pytest.mark.parametrize(
    "num_words",
    [1000, 10_000, 100_000],
    ids=["1K_runs", "10K_runs", "100K_runs"]
)
def test_load_performance_inflect_list(analyzer_instance: MorphAnalyzer, num_words: int):
    """
     Проводит нагрузочное тестирование пакетного метода parse_list.
     """
    print(
        f"\n--- Запуск нагрузочного теста на {num_words} слов ---")

    analyzer = analyzer_instance

    start_time = time.perf_counter()

    analyzer.inflect_list(["слово"] * num_words)

    end_time = time.perf_counter()
    duration = end_time - start_time
    avg_time_per_word = duration / num_words

    ops_per_second = num_words / \
        duration if duration > 0 else float('inf')

    print(f"Итог для {num_words} слов:")
    print(f"  Общее время: {duration:.4f} секунд")
    print(f"  Среднее время на слово: {avg_time_per_word * 1e6:.2f} мкс")
    print(f"  Производительность: {ops_per_second:,.2f} слов/сек")
