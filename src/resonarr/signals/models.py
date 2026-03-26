class ArtistSignals:
    def __init__(
        self,
        rating=None,
        play_count=None,
        normalized_play_ratio=None,
        last_played=None,
        owned_albums=None,
        source=None
    ):
        self.rating = rating
        self.play_count = play_count
        self.normalized_play_ratio = normalized_play_ratio
        self.last_played = last_played
        self.owned_albums = owned_albums or set()
        self.source = source

    def to_dict(self):
        return {
            "rating": self.rating,
            "play_count": self.play_count,
            "normalized_play_ratio": self.normalized_play_ratio,
            "last_played": self.last_played,
            "owned_album_count": len(self.owned_albums),
            "source": self.source
        }