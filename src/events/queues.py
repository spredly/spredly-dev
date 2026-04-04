from enum import Enum


class Queues(str, Enum):
    MATCH_REQUESTS = "match.requests"
    MATCH_RESULTS = "match.results"
