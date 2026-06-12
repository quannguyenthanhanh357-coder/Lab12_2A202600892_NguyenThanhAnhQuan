"""Mood → TMDB genre IDs (https://developer.themoviedb.org/reference/genre-movie-list)."""

MOOD_GENRE_IDS = {
    "happy": [35, 16, 10751, 10402],       # Comedy, Animation, Family, Music
    "sad": [18, 10749],                     # Drama, Romance
    "relaxed": [99, 16, 10751, 35],         # Documentary, Animation, Family, Comedy
    "excited": [28, 878, 12, 53],           # Action, Sci-Fi, Adventure, Thriller
    "romantic": [10749, 10402, 18],         # Romance, Music, Drama
    "scary": [27, 53, 9648],                # Horror, Thriller, Mystery
}

GENRE_NAME_TO_ID = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "sci-fi": 878,
    "science fiction": 878,
    "thriller": 53,
    "war": 10752,
    "western": 37,
}

ALLOWED_MOODS = list(MOOD_GENRE_IDS.keys())
