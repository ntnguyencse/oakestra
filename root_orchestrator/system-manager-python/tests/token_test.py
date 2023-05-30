import logging
import unittest
from datetime import timedelta, datetime
from random import randint

import pytest as pytest
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from secrets import token_hex

from roles.securityUtils import create_jwt_pairing_key_cluster, check_jwt_token_validity

app = Flask(__name__)
jwt = JWTManager(app)


@pytest.fixture(scope='function')
def app(request):
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = token_hex(32)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    app.config["RESET_TOKEN_EXPIRES"] = timedelta(hours=3)  # for password reset
    app.config["JWT_CLUSTER_ACCESS_TOKEN_EXPIRES"] = timedelta(
        hours=5)  # not used as it is inaccessible from securityUtils
    JWTManager(app)

    @app.route('/jwt', methods=['GET'])
    def create_token_endpoint():
        try:
            access_token = create_jwt_pairing_key_cluster(
                "identity",
                timedelta(days=5),
                {
                    "iat": datetime.now(),
                    "aud": "addClusterAPI",
                    "sub": "identity",
                    "clusterName": "dummy2",
                    "location": "1,3,3",
                    "num": str(randint(0, 99999999))
                },
                fresh=True
            )
            return jsonify(jwt=access_token)
        except Exception as e:
            pytest.fail(e)

    @app.route('/check_jwt/<token>', methods=['GET'])
    def check_token(token):
        try:
            print(token)
            return jsonify(check_jwt_token_validity(token))
        except Exception as e:
            print(e)

    return app


def test_base_pairing_token(app):
    # generate token
    test_client = app.test_client()
    response = test_client.get('/jwt')
    token = response.json.get('jwt')

    # validate token
    response = test_client.get("/check_jwt/" + str(token))
    assert response.json.get("sub") == "identity"
