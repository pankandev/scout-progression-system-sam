from ..key import clean_text, join_key, split_key


def test_clean_text():
    assert clean_text("a!\"#b$%&/c()=?d¡") == "abcd"
    assert clean_text("áéíóú") == "áéíóú"
    assert clean_text("-::-") == ""


def test_join_key():
    assert join_key("aa", "b", "cccc") == "aa::b::cccc"


def test_split_key():
    split = split_key("a::b::c")
    assert len(split) == 3
    assert split[0] == "a"
    assert split[1] == "b"
    assert split[2] == "c"
