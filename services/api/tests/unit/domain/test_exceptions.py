import pytest
import app.domain.exceptions as domexc


@pytest.mark.unit
def test_correct_orig():
    some_exception = Exception('InnerErrorText')
    exc = domexc.ModelIntegrityError('Error text', orig=some_exception)
    assert exc.orig == some_exception
    assert str(exc.orig) == "InnerErrorText"