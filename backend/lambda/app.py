import json
from os import environ

import boto3
from urllib.parse import urlparse

from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

sm_runtime_client = boto3.client('sagemaker-runtime')
s3_client = boto3.client('s3')


def get_features(sm_runtime_client, sagemaker_endpoint, payload):
    response = sm_runtime_client.invoke_endpoint(
        EndpointName=sagemaker_endpoint,
        ContentType='text/plain',
        Body=payload)
    response_body = json.loads((response['Body'].read()))
    features = response_body

    return features


def get_neighbors(features, es, k_neighbors=3):
    idx_name = 'idx_movie'
    res = es.search(
        request_timeout=30, index=idx_name,
        body={
            'size': k_neighbors,
            'query': {'knn': {'movie_nlu_vector': {'vector': features, 'k': k_neighbors}}}}
        )
    title = [res['hits']['hits'][x]['_source']['title'] for x in range(k_neighbors)]

    return title


def es_match_query(payload, es, k=3):
    idx_name = 'idx_movie'
    search_body = {
        "_source": {
            "excludes": ["movie_nlu_vector"]
        },
        "highlight": {
            "fields": {
                "description": {}
            }
        },
        "query": {
            "match": {
                "description": {
                    "query": payload
                }
            }
        }
    }

    search_response = es.search(request_timeout=120, index=idx_name,
                                body=search_body)['hits']['hits'][:k]

    # response = [{'title': x['_source']['title'], 'description': x['_source']['description']} for x in search_response]
    response = [{'title': x['_source']['title']} for x in search_response]

    return response



def lambda_handler(event, context):
    # print(event)

    # elasticsearch variables
    service = 'es'
    region = 'us-east-1'
    elasticsearch_endpoint = 'search-nlu-sea-domain-1khc4psmnnoa1-b4y7qwlrgzczk33deigpapqr3e.us-east-1.es.amazonaws.com'

    session = boto3.session.Session()
    credentials = session.get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token
        )

    es = Elasticsearch(
        hosts=[{'host': elasticsearch_endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # sagemaker variables
    sagemaker_endpoint = 'nlu-search-model-1669760440'
    # print(event)
    api_payload = json.loads(event['body'])
    k = api_payload['k']
    payload = api_payload['searchString']

    if 1==2:
        features = get_features(sm_runtime_client, sagemaker_endpoint, payload)
        titles = get_neighbors(features, es, k_neighbors=k)
        # titles= generate_presigned_urls(s3_uris_neighbors)
        return {
            "statusCode": 200,
            # "headers": {
            #     "Access-Control-Allow-Origin":  "*",
            #     "Access-Control-Allow-Headers": "*",
            #     "Access-Control-Allow-Methods": "*"
                
            # },
            "body": json.dumps({
                "title": "hello",
            }),
        }
    else:
        search = es_match_query(payload, es, k)
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            },
            "body": json.dumps(search),
        }
