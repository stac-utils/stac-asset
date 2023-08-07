import importlib.metadata

project = "stac-asset"
copyright = "2023, Pete Gadomski"
author = "Pete Gadomski"
version = importlib.metadata.version("stac_asset")
release = importlib.metadata.version("stac_asset")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
