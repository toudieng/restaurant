import requests

class PaydunyaSetup:
    master_key = "oyur1x1y-z07c-9GId-RLi5-8fdJZGms2hMw"
    private_key = "test_private_TeTacavlljkmIC0JctB3VaPSu6A"
    public_key = "test_public_i0Y7EriVOOHnGl0nRXbfHFQsT1x"
    token = "sARPbruEGYpQWApJHFqi"
    mode = "test"
    store_name = "L'occidental",
    store_tagline = "Restaurant moderne",
    store_phone = "221765879303",
    store_email = "asdieng.elc@gmail.com",
    store_website_url = "http://localhost:8000/accueil/"
    custom_store_logo = ""

    

    @classmethod
    def configure(cls, **kwargs):
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)

class CheckoutInvoice:
    def __init__(self):
        self.items = []
        self.total_amount = 0
        self.description = ""
        self.cancel_url = ""
        self.return_url = ""
        self.url = ""
        self.response_text = ""
        self.customer_name = ""
        self.customer_email = ""
        self.customer_phone_number = ""

    def add_item(self, name, quantity=1, unit_price=0):
        self.items.append({
            "name": name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": unit_price * quantity
        })

    def confirm(self, token):
        url = f"https://app.paydunya.com/sandbox-api/v1/checkout-invoice/confirm/{token}"
        headers = {
            "Content-Type": "application/json",
            "PAYDUNYA-MASTER-KEY": PaydunyaSetup.master_key,
            "PAYDUNYA-PRIVATE-KEY": PaydunyaSetup.private_key,
            "PAYDUNYA-PUBLIC-KEY": PaydunyaSetup.public_key,
            "PAYDUNYA-TOKEN": PaydunyaSetup.token
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"Erreur HTTP {response.status_code}"
            }


    def create(self):
        payload = {
            "invoice": {
                "items": self.items,
                "total_amount": self.total_amount,
                "description": self.description
            },
            "store": {
                "name": PaydunyaSetup.store_name,
                "tagline": PaydunyaSetup.store_tagline,
                "phone": PaydunyaSetup.store_phone,
                "email": PaydunyaSetup.store_email,
                "website_url": PaydunyaSetup.store_website_url,
                "logo_url": PaydunyaSetup.custom_store_logo
            },
            "custom_data": {
                "client_nom": self.customer_name,
                "client_email": self.customer_email,
                "client_telephone": self.customer_phone_number
            },
            "actions": {
                "cancel_url": self.cancel_url,
                "return_url": self.return_url
            }
        }


        url = "https://app.paydunya.com/api/v1/checkout-invoice/create"
        if PaydunyaSetup.mode == "test":
            url = "https://app.paydunya.com/sandbox-api/v1/checkout-invoice/create"

        headers = {
            "Content-Type": "application/json",
            "PAYDUNYA-MASTER-KEY": PaydunyaSetup.master_key,
            "PAYDUNYA-PRIVATE-KEY": PaydunyaSetup.private_key,
            "PAYDUNYA-PUBLIC-KEY": PaydunyaSetup.public_key,
            "PAYDUNYA-TOKEN": PaydunyaSetup.token
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("response_code") == "00":
                self.url = result["response_text"]
                return True
            else:
                self.response_text = result.get("response_text", "Échec sans message clair.")
        else:
            self.response_text = f"Erreur HTTP {response.status_code}"
        return False