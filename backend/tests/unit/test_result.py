import pytest

from core.result import Error, Success, is_error, is_success


def test_success_defaults_and_flags() -> None:
    result = Success(data={"foo": "bar"})
    assert result.ui_type == "text"
    assert result.meta == {}
    assert result.is_ok is True
    assert result.is_err is False
    assert is_success(result)
    assert not is_error(result)


def test_success_with_custom_ui_and_meta() -> None:
    result = Success(data=[1, 2], ui_type="MailCard", meta={"category_count": 4})
    assert result.ui_type == "MailCard"
    assert result.meta == {"category_count": 4}


def test_error_defaults() -> None:
    err = Error(message="upstream 500", user_message="Bir şeyler ters gitti")
    assert err.user_notify is True
    assert err.log_level == "error"
    assert err.retry_after is None
    assert err.is_err is True
    assert err.is_ok is False
    assert is_error(err)
    assert not is_success(err)


def test_error_with_retry_after_and_log_level() -> None:
    err = Error(
        message="rate limited",
        user_message="Çok hızlı oldu, biraz bekle.",
        log_level="warning",
        retry_after=60,
    )
    assert err.log_level == "warning"
    assert err.retry_after == 60


def test_success_and_error_are_frozen() -> None:
    from dataclasses import FrozenInstanceError

    success = Success(data="x")
    err = Error(message="m", user_message="u")
    with pytest.raises(FrozenInstanceError):
        success.data = "y"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        err.message = "z"  # type: ignore[misc]
