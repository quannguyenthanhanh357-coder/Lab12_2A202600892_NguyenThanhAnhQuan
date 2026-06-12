import json
from typing import Any, Dict, List, Optional

from src.tools.mood_config import ALLOWED_MOODS, MOOD_GENRE_IDS
from src.tools.tmdb_client import TMDbClientError, get_client


def _json_ok(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _json_error(message: str, **extra: Any) -> str:
    payload = {"error": message}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def _handle_errors(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TMDbClientError as exc:
            return _json_error(str(exc))
        except ValueError as exc:
            return _json_error(str(exc))

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _pros_cons(detail: Dict[str, Any]) -> Dict[str, List[str]]:
    pros: List[str] = []
    cons: List[str] = []

    rating = detail.get("rating") or 0
    runtime = detail.get("runtime_min") or 0
    vote_count = detail.get("vote_count") or 0

    if rating >= 7.5:
        pros.append(f"Điểm TMDB cao ({rating}/10)")
    elif rating < 6.0 and vote_count > 50:
        cons.append(f"Điểm TMDB thấp ({rating}/10)")

    if vote_count >= 1000:
        pros.append(f"Được {vote_count:,} lượt đánh giá trên TMDB")

    if runtime and runtime <= 100:
        pros.append(f"Thời lượng gọn ({runtime} phút)")
    elif runtime and runtime >= 150:
        cons.append(f"Phim dài ({runtime} phút)")

    if detail.get("plot"):
        pros.append("Có mô tả nội dung từ TMDB")

    if not pros:
        pros.append("Cân nhắc theo sở thích cá nhân")

    return {"pros": pros, "cons": cons}


@_handle_errors
def search_movies(query: str, limit: int = 5) -> str:
    """Search movies on TMDB by title or keyword."""
    if not query.strip():
        return _json_error("query must not be empty")

    limit = max(1, min(int(limit), 10))
    client = get_client()
    movies = client.search_movies(query, limit=limit)
    return _json_ok({"query": query, "source": "TMDB", "count": len(movies), "movies": movies})


@_handle_errors
def get_movie_details(movie_id: int) -> str:
    """Return TMDB details for one movie_id."""
    detail = get_client().get_movie_details(int(movie_id))
    detail["source"] = "TMDB"
    return _json_ok(detail)


@_handle_errors
def filter_by_mood(mood: str, limit: int = 5) -> str:
    """Discover popular TMDB movies matching a mood via genre mapping."""
    mood_key = mood.strip().lower()
    if mood_key not in ALLOWED_MOODS:
        return _json_error(f"mood must be one of {ALLOWED_MOODS}", received=mood)

    limit = max(1, min(int(limit), 10))
    genre_ids = MOOD_GENRE_IDS[mood_key]
    client = get_client()
    movies = client.discover_by_genres(genre_ids, limit=limit)
    return _json_ok(
        {
            "mood": mood_key,
            "source": "TMDB",
            "genre_ids": genre_ids,
            "count": len(movies),
            "movies": movies,
        }
    )


@_handle_errors
def get_similar_movies(movie_id: int, limit: int = 5) -> str:
    """Suggest TMDB similar movies for a movie_id."""
    limit = max(1, min(int(limit), 10))
    payload = get_client().similar_movies(int(movie_id), limit=limit)
    payload["source"] = "TMDB"
    payload["count"] = len(payload["movies"])
    return _json_ok(payload)


@_handle_errors
def check_streaming_availability(movie_id: int, country: str = "VN") -> str:
    """Check TMDB watch/providers for streaming/rent/buy in a country."""
    client = get_client()
    detail = client.get_movie_details(int(movie_id))
    providers = client.watch_providers(int(movie_id), country=country)
    providers["title"] = detail["title"]
    providers["source"] = "TMDB"
    return _json_ok(providers)


@_handle_errors
def get_trending_movies(
    region: str = "VN",
    genre: Optional[str] = None,
    period: str = "week",
) -> str:
    """Fetch trending or popular TMDB movies, optionally filtered by genre."""
    movies = get_client().trending_movies(
        region=region,
        genre=genre,
        period=period,
        limit=5,
    )
    return _json_ok(
        {
            "region": region.upper(),
            "period": period,
            "genre_filter": genre,
            "source": "TMDB",
            "count": len(movies),
            "movies": movies,
        }
    )


@_handle_errors
def compare_movies(movie_ids: List[int]) -> str:
    """Compare 2-3 TMDB movies using live ratings and metadata."""
    if not movie_ids or len(movie_ids) < 2:
        return _json_error("provide 2 or 3 TMDB movie_ids")

    movie_ids = [int(mid) for mid in movie_ids[:3]]
    client = get_client()
    rows = []

    for mid in movie_ids:
        detail = client.get_movie_details(mid)
        extras = _pros_cons(detail)
        rows.append(
            {
                "id": detail["id"],
                "title": detail["title"],
                "rating": detail["rating"],
                "genres": detail["genres"],
                "runtime_min": detail["runtime_min"],
                "vote_count": detail.get("vote_count", 0),
                "pros": extras["pros"],
                "cons": extras["cons"],
            }
        )

    winner = max(rows, key=lambda row: row["rating"])["title"]
    return _json_ok({"source": "TMDB", "comparison": rows, "winner_by_rating": winner})


@_handle_errors
def search_person(name: str, limit: int = 5) -> str:
    """Search for a person (actor/director) on TMDB by name. Returns person_id, name, and profile."""
    if not name.strip():
        return _json_error("name must not be empty")

    limit = max(1, min(int(limit), 10))
    client = get_client()
    people = client.search_person(name.strip(), limit=limit)
    return _json_ok(
        {
            "query": name,
            "source": "TMDB",
            "count": len(people),
            "people": people,
        }
    )


@_handle_errors
def get_movies_by_person(person_id: int, role: str = "director", limit: int = 5) -> str:
    """Get list of movies by a person (director or actor). Args: person_id (int), role ('director'|'actor'), limit (int)."""
    role_lower = role.strip().lower()
    if role_lower not in {"director", "actor"}:
        return _json_error("role must be 'director' or 'actor'", received=role)

    limit = max(1, min(int(limit), 10))
    client = get_client()
    movies = client.get_movies_by_person(int(person_id), role=role_lower, limit=limit)
    return _json_ok(
        {
            "person_id": int(person_id),
            "role": role_lower,
            "source": "TMDB",
            "count": len(movies),
            "movies": movies,
        }
    )

