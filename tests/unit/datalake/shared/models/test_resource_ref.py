import pytest

from aje_libs.datalake.shared.models import ResourceRef


@pytest.mark.unit
def test_resource_ref_valid_s3_with_full_uri():
    ref = ResourceRef(provider="s3", location="s3://my-bucket/path/file.parquet")

    assert ref.provider == "s3"
    assert ref.location == "s3://my-bucket/path/file.parquet"
    assert ref.options == {}


@pytest.mark.unit
def test_resource_ref_valid_s3_with_bucket_only():
    # Nombre de bucket simple debe ser válido aunque no empiece con s3://
    ref = ResourceRef(provider="s3", location="my-bucket")

    assert ref.location == "my-bucket"


@pytest.mark.unit
def test_resource_ref_invalid_s3_location_raises():
    with pytest.raises(ValueError):
        ResourceRef(provider="s3", location="INVALID LOCATION")


@pytest.mark.unit
@pytest.mark.parametrize("url", ["http://example.com", "https://example.com/path"])
def test_resource_ref_valid_http_https(url: str):
    ref = ResourceRef(provider="https", location=url)
    assert ref.location == url


@pytest.mark.unit
def test_resource_ref_invalid_http_location_raises():
    with pytest.raises(ValueError):
        ResourceRef(provider="http", location="example.com/without-scheme")


@pytest.mark.unit
@pytest.mark.parametrize(
    "location",
    [
        "file.csv",
        "/tmp/file.csv",
        "s3://bucket/path/file.csv",
    ],
)
def test_resource_ref_valid_csv_locations(location: str):
    ref = ResourceRef(provider="csv", location=location)
    assert ref.location == location


@pytest.mark.unit
def test_resource_ref_invalid_csv_location_raises():
    with pytest.raises(ValueError):
        ResourceRef(provider="csv", location="not-a-path-and-not-s3")


@pytest.mark.unit
def test_resource_ref_invalid_provider_raises():
    with pytest.raises(ValueError):
        ResourceRef(provider="invalid-provider", location="s3://bucket/file")


@pytest.mark.unit
def test_resource_ref_requires_non_empty_location():
    with pytest.raises(ValueError):
        ResourceRef(provider="s3", location="  ")


@pytest.mark.unit
def test_resource_ref_options_must_be_dict():
    with pytest.raises(TypeError):
        ResourceRef(provider="s3", location="s3://bucket/file", options="not-a-dict")  # type: ignore[arg-type]


