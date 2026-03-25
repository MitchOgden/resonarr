class ArtistSignals:
    def __init__(
        self,
        rating=None,
        play_count=None,
        normalized_play_ratio=None,
        last_played=None,
        source=None
    ):
        self.rating = rating
        self.play_count = play_count
        self.normalized_play_ratio = normalized_play_ratio
        self.last_played = last_played
        self.source = source

    def to_dict(self):
        return {
            "rating": self.rating,
            "play_count": self.play_count,
            "normalized_play_ratio": self.normalized_play_ratio,
            "last_played": self.last_played,
            "source": self.source
        }