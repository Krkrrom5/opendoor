from setuptools import setup, find_packages

setup(
    name="opendoor",
    version="4.0.0",
    packages=find_packages(),
    install_requires=[
        "google-genai",
        "pygments",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "opendoor=opendoor.core.app:main_entry",
        ],
    },
    python_requires=">=3.8",
)
