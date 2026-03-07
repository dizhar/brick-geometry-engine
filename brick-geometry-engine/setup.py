from setuptools import setup, find_packages

setup(
    name="brick-geometry-engine",
    version="0.3.0",
    description="LEGO geometry engine with LDraw I/O, collision detection, and stability analysis",
    packages=find_packages(exclude=["tests*", "examples*", "scripts*", "docs*"]),
    python_requires=">=3.11",
    install_requires=[],  # stdlib only
    extras_require={
        "dev": ["pytest>=8.0"],
    },
    package_data={
        "brick_geometry": ["py.typed"],
    },
)
