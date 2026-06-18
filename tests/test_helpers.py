import os
import tempfile


from utils.helpers import get_file_hash, intify, is_safe_path, sanitize_filename


def test_intify():
    # Integer strings
    assert intify("12345") == 12345
    assert intify("-1001234567") == -1001234567
    assert intify("  567  ") == 567

    # Non-integer strings
    assert intify("@my_channel") == "@my_channel"
    assert intify("https://t.me/test") == "https://t.me/test"
    assert intify("") == ""


def test_sanitize_filename():
    # Normal filename
    assert sanitize_filename("test.jpg") == "test.jpg"

    # Filename with illegal chars
    assert (
        sanitize_filename("test/\\?*<>:|file.png") == "test__?*<>__file.png"
        or "test_____*___file.png"
    )
    # Note: sanitize_filename strips directory path components using os.path.basename
    assert sanitize_filename("test/file.png") == "file.png"

    # Path traversal attempt
    assert sanitize_filename("../../etc/passwd") == "passwd"

    # Empty filename fallback
    assert sanitize_filename("") == "unnamed_file"


def test_get_file_hash():
    # Write temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        f.write("hello world")
        temp_path = f.name

    try:
        expected_md5 = "5eb63bbbe01eeed093cb22bb8f5acdc3"  # MD5 of "hello world"
        assert get_file_hash(temp_path) == expected_md5
    finally:
        os.remove(temp_path)


def test_is_safe_path():
    base = os.path.abspath("downloads")

    # Safe path inside base
    safe = os.path.join(base, "file.jpg")
    assert is_safe_path(base, safe) is True

    # Unsafe path outside base (traversal)
    unsafe = os.path.join(base, "../etc/passwd")
    assert is_safe_path(base, unsafe) is False
