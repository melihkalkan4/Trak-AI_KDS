"""Planet client must be a hard stub until the key arrives."""

import pytest
from datetime import date

from visual_validation.api_clients.planet_client import PlanetClient


def test_default_client_is_unavailable():
    c = PlanetClient(api_key="")
    assert c.available is False


def test_search_raises_until_key_lands():
    c = PlanetClient(api_key="")
    with pytest.raises(NotImplementedError):
        c.search_scenes("EVR_01", date(2026, 5, 1), date(2026, 5, 22))


def test_download_raises_until_key_lands():
    c = PlanetClient(api_key="")
    with pytest.raises(NotImplementedError):
        c.download_chip(scene=None)        # type: ignore[arg-type]
