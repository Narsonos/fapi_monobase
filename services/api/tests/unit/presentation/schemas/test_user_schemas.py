import pytest
import app.presentation.schemas as schemas

@pytest.mark.models
def test_empty_string_to_none_conversion():
    data = {
        "username": "   ",
        "old_password": "",
        "new_password": "  \t  "
    }
    model = schemas.PublicUserUpdateModel(**data)
    assert model.username is None
    assert model.old_password is None
    assert model.new_password is None