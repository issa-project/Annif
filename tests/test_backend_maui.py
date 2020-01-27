"""Unit tests for the HTTP backend in Annif"""

import requests.exceptions
import responses
import unittest.mock
import pytest
import annif.backend.maui
from annif.exception import ConfigurationException
from annif.exception import NotSupportedException
from annif.exception import OperationFailedException


@pytest.fixture
def maui_params():
    return {'endpoint': 'http://api.example.org/mauiservice/',
            'tagger': 'dummy',
            'language': 'en'}


@pytest.fixture
def maui(app_project, maui_params):
    maui_type = annif.backend.get_backend("maui")
    maui = maui_type(
        backend_id='maui',
        config_params=maui_params,
        project=app_project)
    return maui


def test_maui_train_cached(maui):
    with pytest.raises(NotSupportedException):
        maui.train("cached")


def test_maui_train_missing_endpoint(document_corpus, project):
    maui_type = annif.backend.get_backend("maui")
    maui = maui_type(
        backend_id='maui',
        config_params={
            'tagger': 'dummy',
            'language': 'en'},
        project=project)

    with pytest.raises(ConfigurationException):
        maui.train(document_corpus)


def test_maui_train_missing_tagger(document_corpus, project):
    maui_type = annif.backend.get_backend("maui")
    maui = maui_type(
        backend_id='maui',
        config_params={
            'endpoint': 'http://api.example.org/mauiservice/',
            'language': 'en'},
        project=project)

    with pytest.raises(ConfigurationException):
        maui.train(document_corpus)


@responses.activate
def test_maui_initialize_tagger_delete_non_existing(maui, maui_params):
    responses.add(responses.DELETE,
                  'http://api.example.org/mauiservice/dummy',
                  status=404,
                  json={"status": 404,
                        "status_text": "Not Found",
                        "message": "The resource does not exist"})
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/',
                  status=200,
                  json={})

    maui._initialize_tagger(params=maui_params)


@responses.activate
def test_maui_initialize_tagger_create_failed(maui, maui_params):
    responses.add(responses.DELETE,
                  'http://api.example.org/mauiservice/dummy',
                  status=404,
                  json={"status": 404,
                        "status_text": "Not Found",
                        "message": "The resource does not exist"})
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/',
                  body=requests.exceptions.RequestException())

    with pytest.raises(OperationFailedException):
        maui._initialize_tagger(params=maui_params)


@responses.activate
def test_maui_upload_vocabulary_failed(maui, maui_params):
    responses.add(responses.PUT,
                  'http://api.example.org/mauiservice/dummy/vocab',
                  body=requests.exceptions.RequestException())

    with pytest.raises(OperationFailedException):
        maui._upload_vocabulary(params=maui_params)


@responses.activate
def test_maui_upload_train_file_failed(maui, document_corpus, maui_params):
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/dummy/train',
                  body=requests.exceptions.RequestException())

    maui._create_train_file(document_corpus)
    with pytest.raises(OperationFailedException):
        maui._upload_train_file(params=maui_params)


@responses.activate
def test_maui_wait_for_train_failed(maui, maui_params):
    responses.add(responses.GET,
                  'http://api.example.org/mauiservice/dummy/train',
                  body=requests.exceptions.RequestException())

    with pytest.raises(OperationFailedException):
        maui._wait_for_train(params=maui_params)


def test_maui_train_nodocuments(maui, project, empty_corpus):
    with pytest.raises(NotSupportedException) as excinfo:
        maui.train(empty_corpus)
    assert 'training backend maui with no documents' in str(excinfo.value)


@responses.activate
def test_maui_train(maui, document_corpus, app_project):
    responses.add(responses.DELETE,
                  'http://api.example.org/mauiservice/dummy',
                  status=204)
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/',
                  status=200,
                  json={})
    responses.add(responses.PUT,
                  'http://api.example.org/mauiservice/dummy/vocab',
                  status=200,
                  body="")
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/dummy/train',
                  status=200,
                  body="")
    responses.add(responses.GET,
                  'http://api.example.org/mauiservice/dummy/train',
                  status=200,
                  json={"completed": False})
    responses.add(responses.GET,
                  'http://api.example.org/mauiservice/dummy/train',
                  status=200,
                  json={"completed": True})

    maui.train(document_corpus)


@responses.activate
def test_maui_suggest(maui, project):
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/dummy/suggest',
                  json={'title': '1 recommendation from dummy',
                        'topics': [{'id': 'http://example.org/maui',
                                    'label': 'maui',
                                    'probability': 1.0}]})

    result = maui.suggest('this is some text')
    assert len(result) == 1
    assert result[0].uri == 'http://example.org/maui'
    assert result[0].label == 'maui'
    assert result[0].score == 1.0
    assert len(responses.calls) == 1


@responses.activate
def test_maui_suggest_zero_score(maui, project):
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/dummy/suggest',
                  json={'title': '1 recommendation from dummy',
                        'topics': [{'id': 'http://example.org/maui',
                                    'label': 'maui',
                                    'probability': 0.0}]})

    result = maui.suggest('this is some text')
    assert len(result) == 0
    assert len(responses.calls) == 1


def test_maui_suggest_error(maui, project):
    with unittest.mock.patch('requests.post') as mock_request:
        mock_request.side_effect = requests.exceptions.RequestException(
            'failed')

        result = maui.suggest('this is some text')
        assert len(result) == 0


def test_maui_suggest_json_fails(maui, project):
    with unittest.mock.patch('requests.post') as mock_request:
        # create a mock response whose .json() method raises a ValueError
        mock_response = unittest.mock.Mock()
        mock_response.json.side_effect = ValueError("JSON decode failed")
        mock_request.return_value = mock_response

        result = maui.suggest('this is some text')
        assert len(result) == 0


@responses.activate
def test_maui_suggest_unexpected_json(maui, project):
    responses.add(responses.POST,
                  'http://api.example.org/mauiservice/dummy/suggest',
                  json=["spanish inquisition"])

    result = maui.suggest('this is some text')
    assert len(result) == 0
    assert len(responses.calls) == 1
