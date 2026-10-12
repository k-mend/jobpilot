"""Registry that assembles the enabled job sources based on settings."""
from __future__ import annotations

from typing import List

from app.config import Settings, get_settings
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.ats import AshbySource, GreenhouseSource, LeverSource
from app.sources.base import JobSource
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource


def build_sources(settings: Settings = None) -> List[JobSource]:
    settings = settings or get_settings()
    sources: List[JobSource] = [
        RemotiveSource(),
        RemoteOKSource(),
        ArbeitnowSource(),
    ]
    for board in settings.greenhouse_board_list:
        sources.append(GreenhouseSource(board))
    for board in settings.lever_board_list:
        sources.append(LeverSource(board))
    for board in settings.ashby_board_list:
        sources.append(AshbySource(board))
    return sources
