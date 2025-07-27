from restaurant_app.paydunya_sdk.checkout import PaydunyaSetup

PaydunyaSetup.configure(
    master_key = "oyur1x1y-z07c-9GId-RLi5-8fdJZGms2hMw",
    private_key = "test_private_TeTacavlljkmIC0JctB3VaPSu6A",
    public_key = "test_public_i0Y7EriVOOHnGl0nRXbfHFQsT1x",
    token = "sARPbruEGYpQWApJHFqi",
    mode = "test",  # ou "live"
    store_name = "L'occidental",
    store_tagline = "Restaurant moderne",
    store_phone = "221765879303",
    store_email = "asdieng.elc@gmail.com",
    store_website_url = "http://localhost:8000/accueil/"
)
