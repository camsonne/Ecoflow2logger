import hashlib
import hmac

from ecoflow_logger.api import _sign


def test_sign_orders_request_params_before_auth_params():
    # EcoFlow signs (sorted request params) + "&" + (sorted auth params),
    # not one big dict of everything sorted together. Confirmed against
    # a known-working reference implementation
    # (github.com/Mark-Hicks/ecoflow-api-examples).
    request_params = {"sn": "SN1"}
    auth_params = {"accessKey": "ak", "nonce": "123", "timestamp": "1000"}
    expected_str = "sn=SN1&accessKey=ak&nonce=123&timestamp=1000"
    expected = hmac.new(b"secret", expected_str.encode(), hashlib.sha256).hexdigest()

    assert _sign(request_params, auth_params, "secret") == expected


def test_sign_with_no_request_params_uses_auth_params_only():
    auth_params = {"accessKey": "ak", "nonce": "123", "timestamp": "1000"}
    expected_str = "accessKey=ak&nonce=123&timestamp=1000"
    expected = hmac.new(b"secret", expected_str.encode(), hashlib.sha256).hexdigest()

    assert _sign({}, auth_params, "secret") == expected


def test_sign_sorts_within_each_group_independent_of_input_order():
    a = _sign({"b": 2, "a": 1}, {"z": 1, "y": 2}, "secret")
    b = _sign({"a": 1, "b": 2}, {"y": 2, "z": 1}, "secret")
    assert a == b


def test_sign_flattens_nested_dicts():
    a = _sign({}, {"outer": {"inner": 1}}, "secret")
    b = _sign({}, {"outer.inner": 1}, "secret")
    assert a == b
