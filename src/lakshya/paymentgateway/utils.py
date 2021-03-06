from hashlib import sha512
import requests

from paymentgateway.constants import PG_KEY_CLASS_MAP
# from paymentgateway.models import CurrencyExchangeRate


def get_gateway_object(name):
    pg_class = PG_KEY_CLASS_MAP.get(name)
    return pg_class()


def get_gateway_class_from_slug(slug):
    return PG_KEY_CLASS_MAP.get(slug, None) if slug else None
