# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os
import subprocess

sys.path.insert(0, os.path.abspath('../..'))


def get_git_version():
    """
    Get current version.

    Returns: version string
    """
    git = subprocess.Popen(
        ['git', 'describe', '--tags'], stdout=subprocess.PIPE)
    result = git.stdout.readlines()
    if len(result) > 0:
        return result[0].decode().strip()
    else:
        return 'undefined'

def get_git_release():
    """
    Get current release.

    Returns: release string (latest tag)
    """
    git = subprocess.Popen(
        ['git', 'describe', '--tags', '--abbrev=0'], stdout=subprocess.PIPE)
    result = git.stdout.readlines()
    if len(result) > 0:
        return result[0].decode().strip()
    else:
        return 'undefined'


project = 'PumaGuard'
copyright = '2025, Pajarito Environmental Education Center Nature Youth Group'
author = 'Pajarito Environmental Education Center Nature Youth Group'
version = get_git_version()
release = get_git_release()

# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-numfig
numfig = True

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx_copybutton',
    'sphinx_new_tab_link',
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.mathjax',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinxcontrib.mermaid',
]

mermaid_version = "11.11.0"

napoleon_google_docstring = False
napoleon_use_param = True
napoleon_use_ivar = True

templates_path = ['_templates']
exclude_patterns: list[str] = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
# html_theme = 'cloud'
html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_css_files = ['_static/custom.css']

html_theme_options = {
    "repository_url": "https://github.com/PEEC-Nature-Youth-Group/pumaguard",
    "use_repository_button": True,
    "use_issues_button": True,
    "home_page_in_toc": True,
}

# -- Options for todo extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html#configuration

todo_include_todos = True

# -- Options for linkcheck builder -------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-the-linkcheck-builder

# Path to CA certificate bundle (e.g., for self-signed proxy certificates)
# Uncomment and set to your CA bundle path:
tls_cacerts = '/etc/ssl/certs/ca-certificates.crt'  # System bundle
