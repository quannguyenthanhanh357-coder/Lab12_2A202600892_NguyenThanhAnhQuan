import os
from typing import Any, Dict, List, Optional

import requests

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
DEFAULT_LANGUAGE = os.getenv("TMDB_LANGUAGE", "vi-VN")
DEFAULT_REGION = os.getenv("TMDB_REGION", "VN")


class TMDbClientError(Exception):
    """Raised when TMDB API calls fail."""


class TMDbClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        region: str = DEFAULT_REGION,
        timeout: int = 15,
    ):
        self.api_key = api_key or os.getenv("TMDB_API_KEY")
        self.language = language
        self.region = region
        self.timeout = timeout
        self._genre_names: Dict[int, str] = {}

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise TMDbClientError(
                "TMDB_API_KEY chưa được cấu hình. "
                "Đăng ký miễn phí tại https://www.themoviedb.org/settings/api "
                "và thêm vào file .env."
            )
        return self.api_key

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = dict(params or {})
        query["api_key"] = self._require_api_key()
        query.setdefault("language", self.language)

        url = f"{TMDB_BASE_URL}{path}"
        try:
            response = requests.get(url, params=query, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TMDbClientError(f"TMDB request failed: {exc}") from exc

        payload = response.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            message = payload.get("status_message") or payload.get("errors") or "Unknown TMDB error"
            raise TMDbClientError(str(message))
        return payload

    def load_genre_names(self) -> Dict[int, str]:
        if self._genre_names:
            return self._genre_names
        data = self._get("/genre/movie/list")
        self._genre_names = {g["id"]: g["name"] for g in data.get("genres", [])}
        return self._genre_names

    def genre_names(self, genre_ids: List[int]) -> List[str]:
        names = self.load_genre_names()
        return [names.get(gid, str(gid)) for gid in genre_ids]

    @staticmethod
    def _year(release_date: str) -> Optional[int]:
        if release_date and len(release_date) >= 4:
            return int(release_date[:4])
        return None

    def summarize(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        raw_genre_ids = movie.get("genre_ids") or []
        if raw_genre_ids:
            # Search/discover endpoints return genre_ids as [28, 12, ...]
            genre_ids = raw_genre_ids if isinstance(raw_genre_ids[0], int) else [g["id"] for g in raw_genre_ids]
        elif movie.get("genres"):
            genre_ids = [g["id"] for g in movie["genres"]]
        else:
            genre_ids = []

        genres = self.genre_names(genre_ids) if genre_ids else []
        if not genres and movie.get("genres"):
            genres = [g["name"] for g in movie["genres"]]

        return {
            "id": movie["id"],
            "title": movie.get("title") or movie.get("original_title"),
            "year": self._year(movie.get("release_date", "")),
            "genres": genres,
            "rating": round(float(movie.get("vote_average") or 0), 1),
            "poster_url": f"{TMDB_IMAGE_BASE}/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "backdrop_url": f"{TMDB_IMAGE_BASE}/w1280{movie['backdrop_path']}" if movie.get("backdrop_path") else None,
        }

    def search_movies(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        data = self._get(
            "/search/movie",
            {"query": query.strip(), "include_adult": "false", "page": 1},
        )
        results = data.get("results", [])[:limit]
        return [self.summarize(movie) for movie in results]

    def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        data = self._get(
            f"/movie/{int(movie_id)}",
            {"append_to_response": "credits"},
        )

        director = next(
            (
                person["name"]
                for person in data.get("credits", {}).get("crew", [])
                if person.get("job") == "Director"
            ),
            None,
        )
        cast = [
            person["name"]
            for person in data.get("credits", {}).get("cast", [])[:5]
        ]

        return {
            "id": data["id"],
            "title": data.get("title") or data.get("original_title"),
            "year": self._year(data.get("release_date", "")),
            "genres": [g["name"] for g in data.get("genres", [])],
            "runtime_min": data.get("runtime"),
            "rating": round(float(data.get("vote_average") or 0), 1),
            "vote_count": data.get("vote_count", 0),
            "director": director,
            "cast": cast,
            "plot": data.get("overview") or "",
            "original_language": data.get("original_language"),
            "poster_url": f"{TMDB_IMAGE_BASE}/w500{data['poster_path']}" if data.get("poster_path") else None,
            "backdrop_url": f"{TMDB_IMAGE_BASE}/w1280{data['backdrop_path']}" if data.get("backdrop_path") else None,
        }

    def discover_by_genres(
        self,
        genre_ids: List[int],
        limit: int = 5,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        data = self._get(
            "/discover/movie",
            {
                "with_genres": ",".join(str(g) for g in genre_ids),
                "sort_by": "popularity.desc",
                "include_adult": "false",
                "vote_count.gte": 100,
                "region": (region or self.region).upper(),
                "page": 1,
            },
        )
        return [self.summarize(movie) for movie in data.get("results", [])[:limit]]

    def similar_movies(self, movie_id: int, limit: int = 5) -> Dict[str, Any]:
        source = self.get_movie_details(movie_id)
        data = self._get(f"/movie/{int(movie_id)}/similar", {"page": 1})
        similar = [self.summarize(movie) for movie in data.get("results", [])[:limit]]
        return {"source": source["title"], "movies": similar}

    def watch_providers(self, movie_id: int, country: str = DEFAULT_REGION) -> Dict[str, Any]:
        data = self._get(f"/movie/{int(movie_id)}/watch/providers")
        country_key = country.upper()
        country_data = data.get("results", {}).get(country_key, {})
        providers: Dict[str, List[str]] = {
            "flatrate": [],
            "rent": [],
            "buy": [],
        }

        for bucket in providers:
            for item in country_data.get(bucket, []) or []:
                name = item.get("provider_name")
                if name and name not in providers[bucket]:
                    providers[bucket].append(name)

        available = providers["flatrate"] + providers["rent"]
        return {
            "movie_id": movie_id,
            "country": country_key,
            "link": country_data.get("link"),
            "streaming": providers["flatrate"],
            "rent": providers["rent"],
            "buy": providers["buy"],
            "available_on": available,
        }

    def trending_movies(
        self,
        region: str = DEFAULT_REGION,
        genre: Optional[str] = None,
        period: str = "week",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        period_key = period if period in {"day", "week"} else "week"

        if genre:
            from src.tools.mood_config import GENRE_NAME_TO_ID

            genre_id = GENRE_NAME_TO_ID.get(genre.strip().lower())
            if not genre_id:
                raise TMDbClientError(
                    f"Unknown genre '{genre}'. Examples: Sci-Fi, Action, Romance, Horror."
                )
            return self.discover_by_genres([genre_id], limit=limit, region=region)

        data = self._get(
            f"/trending/movie/{period_key}",
            {"region": region.upper()},
        )
        movies = [self.summarize(movie) for movie in data.get("results", [])[: limit * 2]]

        if region.upper() != "US":
            regional = self._get(
                "/discover/movie",
                {
                    "sort_by": "popularity.desc",
                    "region": region.upper(),
                    "include_adult": "false",
                    "page": 1,
                },
            )
            regional_summaries = [self.summarize(m) for m in regional.get("results", [])[:limit]]
            if regional_summaries:
                return regional_summaries

        return movies[:limit]

    def search_person(self, name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for a person (actor/director) on TMDB by name."""
        data = self._get(
            "/search/person",
            {"query": name.strip(), "include_adult": "false", "page": 1},
        )
        results = data.get("results", [])[:limit]
        return [
            {
                "id": person["id"],
                "name": person.get("name", ""),
                "known_for_department": person.get("known_for_department", ""),
                "profile_path": f"{TMDB_IMAGE_BASE}/w500{person['profile_path']}"
                if person.get("profile_path")
                else None,
                "popularity": person.get("popularity", 0),
            }
            for person in results
        ]

    def get_movies_by_person(
        self, person_id: int, role: str = "director", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get movies for a person by role (director or actor)."""
        role_lower = role.strip().lower()
        if role_lower not in {"director", "actor"}:
            raise TMDbClientError(f"role must be 'director' or 'actor', got '{role}'")

        data = self._get(f"/person/{int(person_id)}", {"append_to_response": "movie_credits"})

        person_name = data.get("name", "Unknown")
        movie_credits = data.get("movie_credits", {})

        if role_lower == "director":
            # Get crew entries where job is "Director"
            crew = movie_credits.get("crew", [])
            movie_ids = [
                m["id"]
                for m in crew
                if m.get("job") == "Director" and m.get("id")
            ]
        else:  # actor
            # Get cast entries
            cast = movie_credits.get("cast", [])
            movie_ids = [m["id"] for m in cast if m.get("id")]

        # Fetch details for each movie
        movies = []
        for movie_id in movie_ids[:limit]:
            try:
                movie_detail = self.get_movie_details(movie_id)
                movies.append(movie_detail)
            except TMDbClientError:
                # Skip movies that fail to load
                continue

        return movies


_client: Optional[TMDbClient] = None


def get_client() -> TMDbClient:
    global _client
    if _client is None:
        _client = TMDbClient()
    return _client
