from setuptools import setup

VERSION = "1.0"
DESCRIPTION = "Engine to parse SEC EDGAR data."

setup(
    name="sec",
    version=VERSION,
    author="Locke Adams",
    author_email="lockeadams@gmail.com",
    description=DESCRIPTION,
    packages=["sec"],
    install_requires=[
        "aiohttp",
        "orjson",
        "pandas",
        "python_dateutil",
        "requests",
        "pre-commit",
        "black",
    ],
)
