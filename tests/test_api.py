import hashlib
import hmac

from ecoflow_logger.api import _sign


def test_sign_is_hmac_sha256_over_sorted_params():
    params = {"accessKey": "ak", "nonce": "123", "timestamp": "1000", "sn": "SN1"}
    expected_query = "accessKey=ak&nonce=123&sn=SN1&timestamp=1000"
    expected = hmac.new(b"secret", expected_query.encode(), hashlib.sha256).hexdigest()

    assert _sign(params, "secret") == expected


def test_sign_changes_with_param_order_in_input_but_not_output():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert _sign(a, "secret") == _sign(b, "secret")


def test_sign_flattens_nested_dicts():
    params = {"outer": {"inner": 1}}
    assert _sign(params, "secret") == _sign({"outer.inner": 1}, "secret")
