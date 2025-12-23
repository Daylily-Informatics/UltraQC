#!/usr/bin/env python
"""
MegaQC is a web application that collects results from multiple runs of MultiQC and
allows bulk visualisation.

See the MegaQC website for installation instructions and documentation:
https://megaqc.info

MegaQC was written by Phil Ewels (http://phil.ewels.co.uk) and Denis Moreno at
SciLifeLab Sweden (
http://www.scilifelab.se)
  : https: //megaqc.info  MegaQC was written by Phil Ewels ( http://phil.ewels.co.uk)  :
https:
 //megaqc.info  MegaQC was written by Phil Ewels ( http://phil.ewels.co.uk)  : https:
//megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
  : https: //megaqc.info  MegaQC was written by Phil Ewels ( http://phil.ewels.co.uk) :
https:
 //megaqc.info  MegaQC was written by Phil Ewels ( http://phil.ewels.co.uk) : https:
//megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
 : https: //megaqc.info  MegaQC was written by Phil Ewels ( http://phil.ewels.co.uk) :
https:
 //megaqc.info  MegaQC was written by Phil Ewels (http://phil.ewels.co.uk) and Denis
Moreno at SciLifeLab Sweden (
http://www.scilifelab.se)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (
http://phil.ewels.co.uk)
: https: //megaqc.info  MegaQC was written by Phil Ewels (http://phil.ewels.co.uk) and
Denis Moreno at SciLifeLab Sweden (http://www.scilifelab.se) and extended by Michael
Milton, Tor Solli- Nowlan and Lukas Heumos.
"""

from setuptools import setup

setup(
    name="megaqc",
    version="0.3.0",
    author="Phil Ewels",
    author_email="phil.ewels@scilifelab.se",
    description="Collect and visualise data across multiple MultiQC runs",
    long_description=__doc__,
    keywords=[
        "bioinformatics",
        "biology",
        "sequencing",
        "NGS",
        "next generation sequencing",
        "quality control",
    ],
    url="https://megaqc.info/",
    download_url="https://github.com/MultiQC/MegaQC/releases",
    license="GPLv3",
    packages=["megaqc"],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "megaqc = megaqc.cli:main",
        ],
    },
    install_requires=[
        # Core FastAPI dependencies
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.22.0",
        "starlette>=0.27.0",
        # Database
        "sqlalchemy[asyncio]>=2.0.0",
        "alembic>=1.11.0",
        "aiosqlite>=0.19.0",  # For async SQLite support
        "asyncpg>=0.28.0",  # For async PostgreSQL support
        # Authentication
        "argon2-cffi>=21.0.0",
        "passlib>=1.7.4",
        "python-jose[cryptography]>=3.3.0",
        "python-multipart>=0.0.6",
        # Serialization
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "marshmallow>=3.19.0",
        # Templates and rendering
        "jinja2>=3.1.0",
        "markupsafe>=2.1.0",
        "markdown>=3.4.0",
        # CLI
        "click>=8.0.0",
        "typer>=0.9.0",
        # Scheduling
        "apscheduler>=3.10.0",
        # Data processing
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "plotly>=5.0.0",
        "flatten_json>=0.1.13",
        "outlier-utils>=0.0.3",
        # Utilities
        "pyyaml>=6.0",
        "environs>=9.5.0",
        "httpx>=0.24.0",  # For async HTTP client
        "aiofiles>=23.0.0",  # For async file operations
        # MultiQC integration
        "multiqc>=1.14",
    ],
    extras_require={
        "dev": [
            # Testing
            "pytest>=7.3.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "factory-boy>=3.2.0",
            "asgi-lifespan>=2.1.0",
            # Lint and code style
            "ruff>=0.0.270",
            "black>=23.0.0",
            "isort>=5.12.0",
            "pre-commit>=3.3.0",
            "mypy>=1.3.0",
        ],
        "deploy": ["wheel>=0.40.0"],
        "prod": [
            "asyncpg>=0.28.0",  # PostgreSQL async driver
            "gunicorn>=21.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: JavaScript",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
)
