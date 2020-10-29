import pytest

from core.exceptions.notfound import NotFoundException
from core.services.objectives import ObjectivesService


def test_get_stage():
    prepuberty = ObjectivesService.get_stage_objectives("prepuberty")
    puberty = ObjectivesService.get_stage_objectives("puberty")
    assert prepuberty != puberty


def test_get():
    with pytest.raises(NotFoundException):
        ObjectivesService.get("puberty", "spirituality", 0, 1)
    with pytest.raises(NotFoundException):
        ObjectivesService.get("puberty", "spirituality", 1, 0)
    with pytest.raises(NotFoundException):
        ObjectivesService.get("puberty", "spirituality", 6, 1)
    with pytest.raises(NotFoundException):
        ObjectivesService.get("puberty", "spirituality", 1, 3)
    ObjectivesService.get("puberty", "spirituality", 1, 1)

