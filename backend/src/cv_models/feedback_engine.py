"""
feedback_engine.py
------------------
Unified feedback aggregator and HUD renderer for the AI Interview Trainer — V2.

Responsibilities
~~~~~~~~~~~~~~~~
* ``FeedbackSnapshot`` — typed dataclass that aggregates one frame's worth of
  outputs from all behaviour-analysis detectors.
* ``FeedbackEngine.compile()`` — merges individual detector results into a
  single ``FeedbackSnapshot``.
* ``FeedbackEngine.render()`` — draws a semi-transparent HUD panel on the
  frame (in-place) that presents all metrics in a clean, colour-coded layout.

HUD panel layout (top-left by default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  ┌──────────────────────────────────────┐
  │       Interview Analysis             │  ← header
  ├──────────────────────────────────────┤
  │  EMO   Emotion:     Happy            │  ← green / yellow / red label
  │  EYE   Eye Contact: 74%  [▓▓▓▓░░]   │  ← score + mini bar
  │  PST   Posture:     Good             │  ← green / yellow / red label
  │  FACE  Faces:       1                │  ← green if ≥1, red if 0
  └──────────────────────────────────────┘

Colour coding
~~~~~~~~~~~~~
* Green  → positive / on-target  (eye contact ≥65 %, good posture, happy/neutral)
* Yellow → borderline / warn     (eye contact 35–65 %)
* Red    → negative / off-target (no eye contact, slouching/leaning, angry/sad)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from src.cv_models.emotion_detection import EmotionResult
from src.cv_models.eye_contact import EyeContactResult
from src.cv_models.posture_detection import PostureResult
from src.utils.config import FeedbackConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeedbackSnapshot:
    """Aggregated behaviour analysis results for one processed frame."""

    emotion: str = "Unknown"
    """Dominant emotion label, e.g. ``"Happy"``."""

    emotion_confidence: float = 0.0
    """FER confidence score in [0.0, 1.0]."""

    eye_contact_score: float = 0.0
    """Smoothed iris-centring score in [0.0, 1.0]."""

    eye_contact: bool = False
    """``True`` when ``eye_contact_score`` meets the contact threshold."""

    posture: str = "Unknown"
    """Posture label: ``"Good"``, ``"Slouching"``, ``"Leaning"``, or ``"Unknown"``."""

    shoulder_tilt_deg: float = 0.0
    """Shoulder line tilt in degrees (diagnostic)."""

    face_count: int = 0
    """Number of faces detected by the Haar cascade in this frame."""

    frame_id: int = 0
    """Monotonically increasing frame counter (useful for logging/export)."""


# ---------------------------------------------------------------------------
# Color palette  (all BGR)
# ---------------------------------------------------------------------------

_C_GREEN  = (80,  210,  80)
_C_YELLOW = (40,  200, 210)
_C_RED    = (60,   60, 220)
_C_WHITE  = (230, 230, 230)
_C_MUTED  = (130, 130, 155)
_C_PANEL  = (18,   18,  32)
_C_BORDER = (55,   55,  80)
_C_HEADER = (160, 160, 200)
_C_TRACK  = (50,   50,  50)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _metric_color(
    value: str | float,
    *,
    is_score: bool = False,
) -> tuple[int, int, int]:
    """Return a BGR colour encoding quality (green/yellow/red)."""
    if is_score:
        assert isinstance(value, float)
        if value >= 0.65:
            return _C_GREEN
        if value >= 0.35:
            return _C_YELLOW
        return _C_RED
    # Label-based
    assert isinstance(value, str)
    _GOOD = {"Good", "Happy", "Neutral", "Surprise"}
    _BAD  = {"Angry", "Sad", "Fear", "Disgust", "Slouching", "Leaning"}
    if value in _GOOD:
        return _C_GREEN
    if value in _BAD:
        return _C_RED
    return _C_YELLOW


def _draw_bar(
    frame:  np.ndarray,
    x:      int,
    y:      int,
    score:  float,
    width:  int = 56,
    height: int = 7,
    color:  tuple[int, int, int] = _C_GREEN,
) -> None:
    """Render a compact horizontal progress bar at pixel position (x, y)."""
    filled = int(width * max(0.0, min(1.0, score)))
    # Track background
    cv2.rectangle(frame, (x, y), (x + width, y + height), _C_TRACK, cv2.FILLED)
    # Filled segment
    if filled > 0:
        cv2.rectangle(frame, (x, y), (x + filled, y + height), color, cv2.FILLED)
    # 1-px border
    cv2.rectangle(frame, (x, y), (x + width, y + height), _C_BORDER, 1)


# ---------------------------------------------------------------------------
# FeedbackEngine
# ---------------------------------------------------------------------------


class FeedbackEngine:
    """
    Aggregates per-module detector outputs and renders the analysis HUD.

    Parameters
    ----------
    config : FeedbackConfig
        Controls panel position, width, opacity, and row height.

    Example
    -------
    .. code-block:: python

        engine   = FeedbackEngine(FeedbackConfig())
        snapshot = engine.compile(
            emotion_result=emo,
            eye_result=eye,
            posture_result=pst,
            face_count=1,
            frame_id=42,
        )
        engine.render(frame, snapshot)
    """

    _FONT       = cv2.FONT_HERSHEY_DUPLEX
    _FONT_SM    = cv2.FONT_HERSHEY_SIMPLEX
    _FS_TAG     = 0.45   # font scale for row tag text  e.g. "EMO:"
    _FS_VAL     = 0.50   # font scale for row value text e.g. "Happy"
    _FS_TITLE   = 0.40   # font scale for panel header
    _TH         = 1      # text thickness

    def __init__(self, config: FeedbackConfig) -> None:
        self._cfg = config
        logger.info("FeedbackEngine initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(
        self,
        *,
        emotion_result:  EmotionResult,
        eye_result:      EyeContactResult,
        posture_result:  PostureResult,
        face_count:      int,
        frame_id:        int = 0,
    ) -> FeedbackSnapshot:
        """
        Merge per-detector results into a single ``FeedbackSnapshot``.

        All parameters are keyword-only to prevent accidental argument
        transposition.
        """
        return FeedbackSnapshot(
            emotion            = emotion_result.label,
            emotion_confidence = emotion_result.confidence,
            eye_contact_score  = eye_result.score,
            eye_contact        = eye_result.is_contact,
            posture            = posture_result.label,
            shoulder_tilt_deg  = posture_result.shoulder_tilt_deg,
            face_count         = face_count,
            frame_id           = frame_id,
        )

    def render(self, frame: np.ndarray, snapshot: FeedbackSnapshot) -> None:
        """
        Draw the semi-transparent HUD panel onto ``frame`` in-place.

        Parameters
        ----------
        frame : np.ndarray
            BGR uint8 frame to annotate. Modified in-place.
        snapshot : FeedbackSnapshot
            Compiled analysis results for this frame.
        """
        cfg = self._cfg
        px, py   = cfg.panel_x, cfg.panel_y
        pw       = cfg.panel_width
        lh       = cfg.line_height
        rows     = 4
        pad_top  = 22   # pixels reserved for the header row
        pad_bot  = 8
        panel_h  = pad_top + lh * rows + pad_bot

        # ── Semi-transparent panel background ─────────────────────────
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (px, py),
            (px + pw, py + panel_h),
            _C_PANEL,
            cv2.FILLED,
        )
        # Subtle border for depth
        cv2.rectangle(
            overlay,
            (px, py),
            (px + pw, py + panel_h),
            _C_BORDER,
            1,
        )
        cv2.addWeighted(overlay, cfg.panel_alpha, frame, 1.0 - cfg.panel_alpha, 0, frame)

        # ── Header ────────────────────────────────────────────────────
        self._draw_header(frame, px, py, pw)

        # ── Metric rows ───────────────────────────────────────────────
        row_y0 = py + pad_top
        self._draw_emotion_row(frame, snapshot, px + 8, row_y0)
        self._draw_eye_row    (frame, snapshot, px + 8, row_y0 + lh)
        self._draw_posture_row(frame, snapshot, px + 8, row_y0 + lh * 2)
        self._draw_face_row   (frame, snapshot, px + 8, row_y0 + lh * 3)

    # ------------------------------------------------------------------
    # Private — panel header
    # ------------------------------------------------------------------

    def _draw_header(
        self, frame: np.ndarray, px: int, py: int, pw: int
    ) -> None:
        title = "Interview Analysis"
        (tw, _), _ = cv2.getTextSize(title, self._FONT_SM, self._FS_TITLE, 1)
        tx = px + (pw - tw) // 2
        cv2.putText(
            frame, title,
            (tx, py + 13),
            self._FONT_SM, self._FS_TITLE, _C_HEADER, 1, cv2.LINE_AA,
        )
        # Divider line
        cv2.line(
            frame,
            (px + 6, py + 18),
            (px + pw - 6, py + 18),
            _C_BORDER, 1,
        )

    # ------------------------------------------------------------------
    # Private — helper for tag + value text pair
    # ------------------------------------------------------------------

    def _put_row(
        self,
        frame: np.ndarray,
        tag:   str,
        value: str,
        x:     int,
        y:     int,
        color: tuple[int, int, int],
    ) -> int:
        """
        Render ``"TAG:  value"`` at ``(x, y)``.

        Returns the x pixel coordinate immediately after the value text
        (used by bar-chart rows to place the progress bar).
        """
        tag_str = f"{tag}: "
        cv2.putText(
            frame, tag_str, (x, y),
            self._FONT, self._FS_TAG, _C_MUTED, self._TH, cv2.LINE_AA,
        )
        (tw, _), _ = cv2.getTextSize(tag_str, self._FONT, self._FS_TAG, self._TH)
        cv2.putText(
            frame, value, (x + tw, y),
            self._FONT, self._FS_VAL, color, self._TH, cv2.LINE_AA,
        )
        (vw, _), _ = cv2.getTextSize(value, self._FONT, self._FS_VAL, self._TH)
        return x + tw + vw

    def _row_baseline(self, row_top_y: int) -> int:
        """Return the text baseline y for a row whose top is at row_top_y."""
        return row_top_y + self._cfg.line_height - 9

    # ------------------------------------------------------------------
    # Private — individual metric rows
    # ------------------------------------------------------------------

    def _draw_emotion_row(
        self, frame: np.ndarray, s: FeedbackSnapshot, x: int, top_y: int
    ) -> None:
        color = _metric_color(s.emotion)
        self._put_row(frame, "EMO", s.emotion, x, self._row_baseline(top_y), color)

    def _draw_eye_row(
        self, frame: np.ndarray, s: FeedbackSnapshot, x: int, top_y: int
    ) -> None:
        pct   = int(s.eye_contact_score * 100)
        color = _metric_color(s.eye_contact_score, is_score=True)
        y     = self._row_baseline(top_y)

        # Text
        after_x = self._put_row(frame, "EYE", f"{pct}%", x, y, color)

        # Progress bar — fill remaining panel width
        bar_x = after_x + 6
        bar_w = (self._cfg.panel_x + self._cfg.panel_width) - bar_x - 10
        if bar_w > 12:
            bar_y = y - 8
            _draw_bar(frame, bar_x, bar_y, s.eye_contact_score, width=bar_w, color=color)

    def _draw_posture_row(
        self, frame: np.ndarray, s: FeedbackSnapshot, x: int, top_y: int
    ) -> None:
        color = _metric_color(s.posture)
        self._put_row(frame, "PST", s.posture, x, self._row_baseline(top_y), color)

    def _draw_face_row(
        self, frame: np.ndarray, s: FeedbackSnapshot, x: int, top_y: int
    ) -> None:
        color = _C_GREEN if s.face_count > 0 else _C_RED
        self._put_row(
            frame, "FACE", str(s.face_count),
            x, self._row_baseline(top_y), color,
        )
