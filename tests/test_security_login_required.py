
import pytest


@pytest.mark.parametrize(
  "path,method",
  [
    ("/api/gastos", "GET"),
    ("/api/gastos", "POST"),
    ("/api/resumen", "GET"),
    ("/api/sugerir", "GET"),
    ("/api/categorias", "GET"),
  ],
)
def test_api_requires_login(client, path, method):
  fn = getattr(client, method.lower())
  r = fn(path)
  assert r.status_code in (302, 303, 401)
