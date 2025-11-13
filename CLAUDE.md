# CLAUDE.md

## Project Restructuring Overview

This document describes the restructuring of the Movie NFO Creator project to follow Python best practices and standards.

### Changes Made

#### 1. New Project Structure

The project has been restructured to use the modern `src/` layout, which is recommended by Python packaging standards (PEP 517/518):

```
Movie-NFO-Creator/
├── src/
│   └── movie_nfo_creator/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── utils.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── tmdb.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── csv_parser.py
│       │   └── nfo_parser.py
│       └── nfo/
│           ├── __init__.py
│           └── operations.py
├── awards/
├── pyproject.toml
├── requirements.txt
├── config.ini.dist
├── README.md
├── LICENSE.md
└── .gitignore
```

#### 2. Module Organization

The monolithic `script.py` has been split into logical modules:

- **`api/tmdb.py`**: All TMDB API interaction functions
  - `search_movie_tmdb()`
  - `get_movie_by_tmdb_id()`
  - `get_movie_by_imdb_id()`
  - `get_movie_credits()`
  - `find_tmdb_movie()`

- **`parsers/csv_parser.py`**: CSV file parsing functions
  - `parse_letterboxd_csv()`
  - `parse_movie_id_csv_into_id_array()`
  - `parse_awards()`
  - `is_movie_in_letterboxd_list()`
  - `append_movie_to_csv()`

- **`parsers/nfo_parser.py`**: NFO XML parsing functions
  - `parse_movie_nfo_imdb()`
  - `parse_movie_nfo_xml()`
  - `get_movie_element()`
  - `get_movie_elements()`

- **`nfo/operations.py`**: NFO file creation and modification
  - `create_movie_nfo()`
  - `prompt_create_movie_nfo()`
  - `add_tag_to_movie_nfo()`
  - `add_playcount_to_nfo()`
  - `indent_xml()`

- **`utils.py`**: Utility functions
  - `print_error()`
  - `are_roughly_equals()`
  - `parse_title_and_year()`

- **`cli.py`**: Main CLI application logic
  - `main()` - Entry point for the application
  - `load_properties()`
  - `find_mkv_files()`
  - `ask_and_append_movie_to_watched_override()`

#### 3. Modern Python Packaging

**`pyproject.toml`**: Modern Python package configuration following PEP 517/518
- Defines project metadata
- Specifies dependencies
- Configures console script entry point: `movie-nfo-creator`
- Uses setuptools build backend

**`requirements.txt`**: Lists production dependencies
- Simple format for pip installation
- Currently only requires `requests`

#### 4. Entry Points

The package can now be run in multiple ways:

```bash
# As a module (old way, still works)
python -m movie_nfo_creator

# After installation (new way)
movie-nfo-creator

# Development installation
pip install -e .
```

#### 5. Benefits of This Structure

1. **Modularity**: Code is organized into logical, reusable modules
2. **Maintainability**: Easier to find and modify specific functionality
3. **Testability**: Each module can be tested independently
4. **Standards Compliance**: Follows PEP 8, PEP 517/518
5. **Discoverability**: Clear structure makes it easy for new contributors
6. **Installability**: Can be installed as a proper Python package
7. **Separation of Concerns**: Each module has a single, well-defined purpose

### Installation

#### Development Installation

```bash
# Clone the repository
git clone https://github.com/adrienbricchi/Movie-NFO-Creator.git
cd Movie-NFO-Creator

# Install in development mode
pip install -e .
```

#### Production Installation

```bash
pip install git+https://github.com/adrienbricchi/Movie-NFO-Creator.git
```

### Usage

After installation, you can run the tool from any directory:

```bash
movie-nfo-creator
```

The tool will look for `config.ini` in the current working directory.

### Future Improvements

Potential enhancements to the project structure:

1. **Testing**: Add `tests/` directory with unit tests
2. **Documentation**: Add `docs/` directory with Sphinx documentation
3. **Type Hints**: Add type annotations throughout the codebase
4. **CLI Arguments**: Use `argparse` or `click` for command-line options
5. **Logging**: Replace print statements with proper logging
6. **Configuration**: Support multiple config file locations or environment variables
7. **Data Files**: Consider moving `awards/` to `src/movie_nfo_creator/data/`
8. **CI/CD**: Add GitHub Actions for testing and releases

### Notes

- The original `script.py` is retained for backward compatibility but should be considered deprecated
- All API functions now accept `api_key` parameter instead of using global variable
- Import structure uses relative imports within the package
- Each subpackage has an `__init__.py` with `__all__` exports for clean public API
