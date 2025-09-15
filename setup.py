from setuptools import setup, find_packages

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
    package_data={
        'steosmorphy': ['*.dll', '*.so', '*.dylib', '*.dawg', '*.dawg.zst'],
    },
    zip_safe=False,
    install_requires=[
        'zstandard',
        'tqdm',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Go',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Text Processing :: Linguistic',
    ],
    python_requires='>=3.7',
)
