from flask import json, jsonify, request, Blueprint
from constants import CLIENT_ID, DOMAIN, ALGORITHMS
from six.moves.urllib.request import urlopen
from jose import jwt
from flask import session

auth_bp = Blueprint('auth', __name__)


# NOT BING: START
# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069
# .349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@auth_bp.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    # print(f'Request headers: {request.headers}')
    # if 'Authorization' in request.headers:
    #     auth_header = request.headers['Authorization'].split()
    #     token = auth_header[1]
    # else:
    #     raise AuthError(
    #         {"code": "no auth header",
    #          "description":
    #              "Authorization header is missing"}, 401
    #         )
    if 'user' in session:
        token = session["user"]
    else:
        return
        # raise AuthError(
        #     {"code": "no auth header",
        #      "description":
        #         "Authorization header is missing"}, 401
        #      )
    # print("Authorization header exists")

    jsonurl = urlopen("https://" + DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    # print("JWKS")
    # print(jwks)
    try:
        unverified_header = jwt.get_unverified_header(token)
        # print("UNVERIFIED_HEADER")
        # print(unverified_header)
    except jwt.JWTError:
        raise AuthError(
            {"code": "invalid_header",
             "description":
                 "Invalid header. "
                 "Use an RS256 signed JWT Access Token"}, 401
        )
    # print("Authorization header valid")

    if unverified_header["alg"] == "HS256":
        raise AuthError(
            {"code": "invalid_header",
             "description":
                 "Invalid header. "
                 "Use an RS256 signed JWT Access Token"}, 401
        )
    # print("Authorization header not HS256")

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://" + DOMAIN + "/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError(
                {"code": "token_expired",
                 "description": "token is expired"}, 401
            )

        except jwt.JWTClaimsError:
            raise AuthError(
                {"code": "invalid_claims",
                 "description":
                     "incorrect claims,"
                     " please check the audience and issuer"}, 401
            )

        except Exception:
            raise AuthError(
                {"code": "invalid_header",
                 "description":
                     "Unable to parse authentication"
                     " token."}, 401
            )

        # print("token not expired")
        # print("claims valid")
        # print("authentication parsed")

        return payload
    else:
        # print("no RSA key")
        raise AuthError(
            {"code": "no_rsa_key",
             "description":
                 "No RSA key in JWKS"}, 401
        )


# Decode the JWT supplied in the Authorization header
@auth_bp.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload

# NOT BING: END
