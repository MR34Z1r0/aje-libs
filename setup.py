from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aje-libs",
    version="0.1.0",  # Usa versionado semántico
    author="Miguel Espinoza Alvarez",
    author_email="mespinoza1388@gmail.com",
    description="Librería de utilidades para los proyectos de AWS en Ajegroup",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MR34Z1r0/aje-libs",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["aje_libs*"]),
    install_requires=[
        # Lista tus dependencias aquí, por ejemplo:
        "aws-lambda-powertools>=3.11.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)