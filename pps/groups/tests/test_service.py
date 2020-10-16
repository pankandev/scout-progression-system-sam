from ..app import GroupsService


def test_generate_beneficiary_code():
    code = GroupsService.generate_beneficiary_code("district", "code")
    assert type(code) is str
    assert len(code) == 8
