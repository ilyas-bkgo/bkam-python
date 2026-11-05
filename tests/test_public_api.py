import bkam


def test_public_names_are_importable():
    for name in bkam.__all__:
        assert hasattr(bkam, name), f"{name} is listed in __all__ but missing"


def test_main_classes_are_exposed():
    assert bkam.BKAMClient.__name__ == "BKAMClient"
    assert issubclass(bkam.AuthenticationError, bkam.APIError)
    assert issubclass(bkam.APIError, bkam.BKAMError)


def test_version_is_a_string():
    assert isinstance(bkam.__version__, str)
    assert bkam.__version__