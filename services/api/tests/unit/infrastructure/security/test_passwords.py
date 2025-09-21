import pytest
from app.infrastructure.security.passwords import BCryptHasher


def test_bcrypt_hash_and_verify():
    hasher = BCryptHasher()
    pw = 'sup3rS3cret!'
    h = hasher.hash(pw)
    assert isinstance(h, str)
    assert h != pw
    # verify correct password
    assert hasher.verify(pw, h) is True
    # incorrect password
    assert hasher.verify('wrongpw', h) is False


def test_bcrypt_salt_uniqueness():
    hasher = BCryptHasher()
    pw = 'repeat'
    h1 = hasher.hash(pw)
    h2 = hasher.hash(pw)
    # Due to salt, two hashes for same password should differ
    assert h1 != h2
    assert hasher.verify(pw, h1) is True
    assert hasher.verify(pw, h2) is True


def test_bcrypt_hash_format_and_type_error():
    hasher = BCryptHasher()
    pw = 'formatpw'
    h = hasher.hash(pw)
    # bcrypt hashes start with $2b$ or $2a$
    assert h.startswith('$2')

    # passing non-string should raise an AttributeError when trying to encode
    with pytest.raises(AttributeError):
        hasher.hash(None)
