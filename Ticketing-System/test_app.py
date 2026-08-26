from app import app

def test_homepage():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200

if __name__ == "__main__":
    test_homepage()
    print("Application test PASSED")


print("Jenkins automated test execution confirmed")