import pytest
from pydantic import ValidationError

from app.enums import ProjectRole
from app.exceptions import ValidationFailed
from app.schemas import MAX_PAGE_SIZE, PageParams, PatchSchema, check_sort


def test_project_role_levels():
    assert ProjectRole.OWNER.level > ProjectRole.ADMIN.level
    assert ProjectRole.ADMIN.level > ProjectRole.MEMBER.level
    assert ProjectRole.MEMBER.level > ProjectRole.VIEWER.level


def test_check_sort_default():
    assert check_sort(None, {"created_at"}, "-created_at") == "-created_at"


def test_check_sort_allowed():
    assert check_sort("-title", {"title", "created_at"}, "-created_at") == "-title"


def test_check_sort_unknown_field():
    with pytest.raises(ValidationFailed):
        check_sort("password", {"title"}, "-created_at")


def test_page_params_default():
    params = PageParams(page=1, page_size=20)
    assert params.page == 1
    assert params.page_size == 20
    assert params.offset == 0


def test_page_params_offset():
    params = PageParams(page=3, page_size=10)
    assert params.offset == 20


def test_page_params_invalid_size():
    with pytest.raises(ValidationFailed):
        PageParams(page_size=MAX_PAGE_SIZE + 1)


def test_page_params_invalid_page():
    with pytest.raises(ValidationFailed):
        PageParams(page=0)


class DummyPatch(PatchSchema):
    """Patch payload with one nullable field for tests."""

    title: str | None = None


def test_patch_schema_changes_excludes_unset():
    patch = DummyPatch()
    assert patch.changes() == {}


def test_patch_schema_changes_keeps_explicit_null():
    patch = DummyPatch(title=None)
    assert patch.changes() == {"title": None}


def test_patch_schema_rejects_unknown_field():
    with pytest.raises(ValidationError):
        DummyPatch(unknown_field="x")
