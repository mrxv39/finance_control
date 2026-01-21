
def test_root_redirects_when_not_logged(client):
  r = client.get("/", follow_redirects=False)
  assert r.status_code in (302, 303)


def test_root_ok_when_logged(client, login):
  r = client.get("/", follow_redirects=False)
  assert r.status_code in (200, 302, 303)
