import jwt
import requests

from hashlib import sha256

from fastapi import HTTPException
from skynet.env import asap_pub_keys_url, asap_pub_keys_folder

def get_public_key(path: str) -> str:
    requests_url = f'{asap_pub_keys_url}/{path}'

    print(f'Fetching public key from {requests_url}')

    req = requests.get(requests_url)
    pub_key = req.text

    return pub_key

def authorize(jwt_incoming: str) -> bool:
    try:
        token_header = jwt.get_unverified_header(jwt_incoming)
    except Exception:
        raise HTTPException(status_code=401, detail='Failed to decode JWT header')

    if 'kid' not in token_header:
        raise HTTPException(status_code=401, detail="Invalid token. No kid header.")

    kid = token_header["kid"]
    is_jaas = kid.startswith('vpaas-magic-cookie')
    tenant = kid.split('/')[0] if is_jaas else None
    folder = f'vpaas/{asap_pub_keys_folder}/{tenant}' if is_jaas else asap_pub_keys_folder

    encoded_pub_key_name = sha256((kid).encode('UTF-8')).hexdigest()
    pub_key_remote_filename = f'{encoded_pub_key_name}.pem'

    try:
        public_key = get_public_key(f'{folder}/{pub_key_remote_filename}')
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed to retrieve public key. {pub_key_remote_filename}')

    try:
        jwt.decode(jwt_incoming, public_key, algorithms=['RS256', 'HS512'])
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed decoding JWT with public key {pub_key_remote_filename}')
