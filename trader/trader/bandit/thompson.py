import random

def thompson_sample(alpha: float, beta: float) -> float:
    # simple beta sampling
    return random.betavariate(alpha, beta)
