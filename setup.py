from setuptools import setup, find_packages

setup(
    name="passxmp",
    version="1.0.0",
    description="Mirror Lightroom presets as DaVinci Resolve .cube LUT files",
    author="Maxwell Thomason",
    url="https://github.com/maxthomason/PassXMP",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "PyQt6>=6.5",
        "watchdog>=3.0",
        "numpy>=1.24",
        "scipy>=1.10",
        "colour-science>=0.4",
        "Pillow>=10.0",
    ],
    entry_points={
        "console_scripts": [
            "passxmp=src.main:main",
        ],
    },
)
