import os
import platform
from setuptools import setup, find_packages

try:  # setuptools >= 70
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # старый путь
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

# Цель: из env (для кросс-сборки) либо хост.
TARGET = os.environ.get("STEOS_TARGET", platform.system()).lower()

# glob_бинаря, тег_платформы_wheel
_PLATFORMS = {
    "linux":   ("*.so",    "manylinux_2_28_x86_64"),
    "windows": ("*.dll",   "win_amd64"),
    "darwin":  ("*.dylib", "macosx_11_0_x86_64"),
}
if TARGET not in _PLATFORMS:
    raise RuntimeError(f"Unsupported target: {TARGET}")
_bin_glob, _plat_tag = _PLATFORMS[TARGET]


class BinaryWheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        # Go-бинарь грузится через ctypes → не зависит от ABI CPython,
        # но привязан к ОС/арх. Любой Python3, без ABI, конкретная платформа.
        return "py3", "none", _plat_tag


setup(
    name='steosmorphy',
    version='1.0.0',
    author='Steos',
    author_email='regger@mind-simulation.com',
    description='Высокопроизводительный морфологический анализатор для Python',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/SteosOfficial/SteosMorphy-py',
    packages=find_packages(),
    cmdclass={"bdist_wheel": BinaryWheel},
    package_data={'steosmorphy': ['*.dawg', '*.dawg.zst', _bin_glob]},
    zip_safe=False,
    install_requires=['zstandard', 'tqdm'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Go',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Text Processing :: Linguistic',
    ],
    python_requires='>=3.7',
)