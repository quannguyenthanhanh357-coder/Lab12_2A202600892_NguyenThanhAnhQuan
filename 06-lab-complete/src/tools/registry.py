import ast
import json
import re
from typing import Any, Callable, Dict, List, Tuple

from src.tools import movie_tools

ToolFn = Callable[..., str]


def _spec(name: str, description: str, fn: ToolFn, example: str) -> Dict[str, Any]:
    return {"name": name, "description": description, "fn": fn, "example": example}


TOOL_SPECS: List[Dict[str, Any]] = [
    _spec(
        "search_movies",
        "Search TMDB by title/keyword. Args: query (str), limit (int, default 5). Returns TMDB movie_id, title, year, genres, rating.",
        movie_tools.search_movies,
        'search_movies("Inception", 5)',
    ),
    _spec(
        "get_movie_details",
        "Get live TMDB details. Args: movie_id (int, TMDB id). Returns plot, runtime, director, cast, rating.",
        movie_tools.get_movie_details,
        "get_movie_details(27205)",
    ),
    _spec(
        "filter_by_mood",
        'Discover TMDB movies by mood via genre mapping. mood: happy, sad, relaxed, excited, romantic, scary. Args: mood (str), limit (int).',
        movie_tools.filter_by_mood,
        'filter_by_mood("romantic", 5)',
    ),
    _spec(
        "get_similar_movies",
        "TMDB similar movies. Args: movie_id (int), limit (int, default 5). Search first if you only know the title.",
        movie_tools.get_similar_movies,
        "get_similar_movies(27205, 5)",
    ),
    _spec(
        "check_streaming_availability",
        'TMDB watch/providers for a country. Args: movie_id (int), country (str ISO, default "VN"). Returns Netflix, Disney+, etc.',
        movie_tools.check_streaming_availability,
        'check_streaming_availability(27205, "VN")',
    ),
    _spec(
        "get_trending_movies",
        'Trending/popular TMDB movies. Args: region (str, default "VN"), genre (str optional, e.g. "Sci-Fi"), period ("day"|"week").',
        movie_tools.get_trending_movies,
        'get_trending_movies("VN", "Sci-Fi", "week")',
    ),
    _spec(
        "compare_movies",
        "Compare 2-3 TMDB movies by live rating/metadata. Args: movie_ids (list of int). Use search_movies to find ids first.",
        movie_tools.compare_movies,
        "compare_movies([27205, 157336, 1124])",
    ),
    _spec(
        "search_person",
        "Search TMDB for a person (actor/director) by name. Args: name (str), limit (int, default 5). Returns person_id, name, profile.",
        movie_tools.search_person,
        'search_person("Tom Hanks", 5)',
    ),
    _spec(
        "get_movies_by_person",
        "Get list of movies by a person. Args: person_id (int, from search_person), role ('director'|'actor', default 'director'), limit (int). Use search_person first to find person_id.",
        movie_tools.get_movies_by_person,
        'get_movies_by_person(2001, "director", 5)',
    ),
]

TOOL_MAP: Dict[str, ToolFn] = {spec["name"]: spec["fn"] for spec in TOOL_SPECS}


def parse_action(action_line: str) -> Tuple[str, List[Any]]:
    """Parse tool_name(arg1, arg2) into name and Python args."""
    text = action_line.strip()
    try:
        node = ast.parse(text, mode="eval").body
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = [ast.literal_eval(ast.unparse(arg)) for arg in node.args]
            return node.func.id, args
    except (SyntaxError, ValueError):
        pass

    match = re.match(r"^(\w+)\((.*)\)\s*$", text, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid action format: {action_line}")

    name = match.group(1)
    args_blob = match.group(2).strip()
    if not args_blob:
        return name, []

    return name, [args_blob.strip("\"'")]


def execute_tool(tool_name: str, args: List[Any]) -> str:
    fn = TOOL_MAP.get(tool_name)
    if not fn:
        available = ", ".join(TOOL_MAP.keys())
        return json.dumps({"error": f"Tool {tool_name} not found. Available: {available}"})

    try:
        return fn(*args)
    except TypeError as exc:
        return json.dumps({"error": f"Invalid arguments for {tool_name}: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"Tool execution failed: {exc}"})
