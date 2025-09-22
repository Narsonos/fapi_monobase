import pytest
from app.infrastructure.security.passwords import BCryptHasher


def test_bcrypt_hash_and_verify():
    hasher = BCryptHasher()
    pw = 'sup3rS3cret!'
    h = hasher.hash(pw)
    assert isinstance(h, str)
    assert h != pw
    assert hasher.verify(pw, h) is True
    assert hasher.verify('wrongpw', h) is False


def test_bcrypt_salt_uniqueness():
    hasher = BCryptHasher()
    pw = 'repeat'
    h1 = hasher.hash(pw)
    h2 = hasher.hash(pw)
    assert h1 != h2
    assert hasher.verify(pw, h1) is True
    assert hasher.verify(pw, h2) is True


def test_bcrypt_hash_format_and_type_error():
    hasher = BCryptHasher()
    pw = 'formatpw'
    h = hasher.hash(pw)
    assert h.startswith('$2')
    with pytest.raises(AttributeError):
        hasher.hash(None)
