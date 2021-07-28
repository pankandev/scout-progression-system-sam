__all__ = ['config']


class ScoutSpiritConfig:
    def __init__(
            self,
            normal_score: int,
            rare_score: int
    ):
        self.normal_score = normal_score
        self.rare_score = rare_score


config = ScoutSpiritConfig(
    normal_score=20,
    rare_score=100
)
