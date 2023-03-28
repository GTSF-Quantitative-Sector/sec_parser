from setuptools import setup

VERSION = "1.0.1"
DESCRIPTION = "Engine to parse SEC EDGAR data."

setup(
    name="sec",
    version=VERSION,
    author="Locke Adams",
    author_email="lockeadams@gmail.com",
    description=DESCRIPTION,
    packages=["sec"],
    package_data={"sec": ["data/processed/*", "data/wacc/*", "data/sp500/*"]},
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
