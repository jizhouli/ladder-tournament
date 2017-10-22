from flask import current_app as app

from zaih_core.caching import cache_for
from zaih_core.verification import get_authorization

from src.models.auth import WXAuthentication, OAuth2Token
from src.settings import Config

def verify_client(token):
    import sys
    print sys._getframe().f_code.co_filename, sys._getframe().f_code.co_name

    if token == Config.DEFAULT_BASIC_TOKEN:
        return True, ['open']
    return False, None


@cache_for(60)
def verify_token(token):
    import sys
    print sys._getframe().f_code.co_filename, sys._getframe().f_code.co_name

    token_info = OAuth2Token.get_token_info(token)
    #print token_info
    if token_info:
        if isinstance(token_info, dict):
            return True, token_info
        try:
            token_info = json.loads(token_info)
        except ValueError:
            return False, None
    return False, None


def verify_request():
    authorization_type, token = get_authorization()
    if authorization_type == 'Basic':
        return verify_client(token)
    elif authorization_type == 'Bearer':
        return verify_token(token)
    return False, None
