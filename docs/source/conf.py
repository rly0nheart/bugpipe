from datetime import datetime

project = "Bugpipe"
copyright = f"{datetime.now().astimezone().year}, Ritchie Mwewa"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_heading_anchors = 3

master_doc = "index"
exclude_patterns: list[str] = []
templates_path = ["_templates"]

html_theme = "alabaster"
html_show_sourcelink = False
html_show_sphinx = False
html_sidebars = {
    "**": ["sidebar.html", "searchbox.html"],
}
html_theme_options = {
    "show_powered_by": False,
    "show_related": False,
}
