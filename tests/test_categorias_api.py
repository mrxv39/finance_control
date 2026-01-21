

def test_categorias_returns_json(client, login):
  r = client.get("/api/categorias")
  assert r.status_code == 200
  data = r.get_json()
  assert isinstance(data, list)
  assert data, "debería devolver categorías base"
  assert {"categoria", "subcategoria", "n"} <= set(data[0].keys())


def test_categorias_filter_q(client, login):
  r = client.get("/api/categorias?q=alim")
  assert r.status_code == 200
  data = r.get_json()
  assert all(("alim" in (x["categoria"] + " " + x["subcategoria"]).lower()) for x in data)
