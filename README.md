# Dungeon Map Planner (name TBD)

The purpose of this app is to make it simple to plan out maps for dungeons, game worlds, etc...

# Code Style

Basic PEP8, plus:

* Qt (PySide2) calls obviously use existing camelCase convention, but follow PEP8 naming otherwise
* Line length limit of 99 characters (still 72 characters for docstrings though)
* Single quotes for single characters, single words, kebab-case-ids, snake_case_ids, and/file/paths
* Double quotes for everything else
* Softwrapped strings should have the space at the beginning of the string on the next line
* When spreading function calls onto multiple lines:
    * No arguments go on the same line as the function name or parens
    * Group positional args together when logical, but put them on their own lines otherwise
    * Put each kwarg on its own line
    * Do not indent the closing parentheses
* Lists and dicts should follow a similar convention
