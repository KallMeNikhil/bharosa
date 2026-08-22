from __future__ import annotations

import random
import uuid

from app.domains.identity import SERIAL_LENGTH

_SERIAL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


class SimulationRandom:
    """A scenario's sole source of randomness, scoped to one seed.

    Cryptographic material (signing keys, BHIP1 serial entropy in production)
    is deliberately never sourced from here — those stay on the platform's
    real CSPRNG, exactly as they would for a genuine manufacturer. What this
    class controls is scenario shape: which identities receive which
    treatment, event timing, geography, and the serial strings used to look
    identities up, so that the same seed reproduces the same scenario
    structure and ground truth every time it is generated.
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def uuid(self) -> uuid.UUID:
        return uuid.UUID(int=self._random.getrandbits(128), version=4)

    def serial(self) -> str:
        return "".join(self._random.choice(_SERIAL_ALPHABET) for _ in range(SERIAL_LENGTH))

    def choice(self, sequence):
        return self._random.choice(sequence)

    def uniform(self, lower: float, upper: float) -> float:
        return self._random.uniform(lower, upper)

    def randint(self, lower: int, upper: int) -> int:
        return self._random.randint(lower, upper)
