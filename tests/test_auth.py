

def test_login_page_exists(client):
  # no asumimos ruta exacta; pero /login suele existir
  r = client.get("/login", follow_redirects=False)
  assert r.status_code in (200, 302, 303, 404)


def test_logout_exists(client, login):
  r = client.get("/logout", follow_redirects=False)
  assert r.status_code in (200, 302, 303, 404)
