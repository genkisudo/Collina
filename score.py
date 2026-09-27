"""Compatibility import for the scoring code in :mod:`polyflag.score`.

Use ``polyflag.score`` for new imports. This module keeps older imports working
without maintaining a second copy of the question definitions.
"""

from polyflag.score import QUESTIONS, score_event

__all__ = ["QUESTIONS", "score_event"]
