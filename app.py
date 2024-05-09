from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

# imports
from minio import Minio
from minio.error import S3Error
import os
import io
import requests
import json

# ignore warnings
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def main():
    payload = request.get_json()
    print(payload, flush=True)

    # MINIO
    # params and variables
    COS_ENDPOINT = os.environ.get("COS_ENDPOINT", "ibm-lh-lakehouse-minio-svc.cp4d.svc.cluster.local:9000")
    COS_ACCESS_KEY = os.environ.get("COS_ACCESS_KEY", "none")
    COS_SECRET_KEY = os.environ.get("COS_SECRET_KEY", "none")
    # APIC
    username = os.environ.get("APIC_USERNAME")
    password = os.environ.get("APIC_PASSWORD")
    APIC_ENDPOINT = os.environ.get("APIC_ENDPOINT")
    APIC_REALM = os.environ.get("APIC_REALM")
    APIC_CLIENT_ID = os.environ.get("APIC_CLIENT_ID")
    APIC_CLIENT_SECRET = os.environ.get("APIC_CLIENT_SECRET")
    APIC_ORG = os.environ.get("APIC_ORG")
    APIC_CATALOG = os.environ.get("APIC_CATALOG")


    # openapi file params
    bucket = "test-gas"
    file_name = "upload/metadata_of_product.json"

    # "test-gas/upload/metadata_of_product.json"
    eventkey = payload['Key']
    print("Event key: " + eventkey)
    path = eventkey.split('/')
    bucket = path[0]
    folder = path[1]
    file_name = path[2]
    print("Parsed event: bucket={0}, folder={1}, filename={2}".format(bucket, folder, file_name))

    # read file from minio

    minio_client = Minio(
        endpoint=COS_ENDPOINT,
        secure=False,
        access_key=COS_ACCESS_KEY,
        secret_key=COS_SECRET_KEY
    )


    print("Retrieving item from bucket: {0}, key: {1}".format(bucket, folder + "/" + file_name))
    try:
        minio_client.fget_object(bucket, folder + "/" + file_name,file_name)
    except S3Error as e:
        e
    
    from pprint import pprint
    # print file
    f = open(file_name, 'r')
    file_contents = f.read()
    metadatafile = json.loads(file_contents)

    pprint (metadatafile)
    f.close()

    apifile_name = metadatafile['files'][0]
    print(apifile_name)

    # get meta data from somewhere
    dp_meta_json = """{"tags":["Financial Services", "Banking", "Insurance"],"providername":"ACME Large Bank","provider":"mp_bk_large_bank_a"}"""
    print(metadatafile['tags'])
    tagsstr = str(metadatafile['tags']).replace('\'', '"')
    print(tagsstr)
    dp_meta_json = "{\"tags\":" + tagsstr + ",\"providername\": \"" + metadatafile['providername'] + "\", \"provider\":\"mp_bk_large_bank_a\"}"
    print(dp_meta_json)

    # load apifile from bucket
    print("Retrieving item from bucket: {0}, key: {1}".format(bucket, folder + "/" + apifile_name))
    try:
        minio_client.fget_object(bucket, folder + "/" + apifile_name, apifile_name)
    except S3Error as e:
        e

    # print file
    f = open(apifile_name, 'r')
    apifile_contents = f.read()
    apifile = json.loads(apifile_contents)

    # pprint (apifile)
    f.close()

    apititle = apifile['info']['title']
    print(apititle)
    print(apifile['info']['x-ibm-name'])
    #title_lower = ''.join(title.split()).lower()
    apiname = apititle.replace(' ', '-').lower()
    apiversion = apifile['info']['version']

    # APIC related setup here

    token_url = APIC_ENDPOINT +  "/api/token"

    token_payload = json.dumps({
        "grant_type": "password",
        "username": username,
        "password": password,
        "realm": APIC_REALM,
        "client_id": APIC_CLIENT_ID,
        "client_secret": APIC_CLIENT_SECRET
    })

    token_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", token_url, headers=token_headers, data=token_payload, verify=False)

    apic_token = json.loads(response.text)['access_token']


    # create api
    org = APIC_ORG
    apic_url = APIC_ENDPOINT +  "/api/orgs/" + org + "/drafts/draft-apis?api_type=rest&gateway_type=datapower-api-gateway"
    #apic_url

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer '+ apic_token
    }

    f = open(apifile_name, 'r')
    openapi = json.load(f)
    f.close()

    payload = json.dumps({
        "draft_api": openapi
    })

    response = requests.request("POST", apic_url, headers=headers, data=payload, verify=False)

    dummy_api = json.loads(response.text)

    # product template
    product_template_json = {
        "info": {
            "version": "#VERSION#",
            "title": "#TITLE#",
            "name": "#NAME#",
            "summary": "#SUMMARY#",
            "categories": [ "#CATEGORIES#" ]
        },
        "gateways": [
            "datapower-api-gateway"
        ],
        "plans": {
            "default-plan": {
                "title": "Default Plan",
                "apis": {
                    "dummy-api1.0.0": {}
                }
            }
        },
        "apis": {
            "dummy-api1.0.0": {
                "name": "dummy-api:1.0.0"
            }
        },
        "product": "1.0.0"
    }

    # customize template
    # get meta data from somewhere
    # dp_meta_json = """{"tags":["Financial Services", "Banking", "Insurance"],"providername":"ACME Large Bank","provider":"mp_bk_large_bank_a"}"""

    product_template_json['info']['version'] = metadatafile['version']
    product_template_json['info']['title'] = metadatafile['name']
    product_template_json['info']['name'] = metadatafile['name'].replace(' ', '-').lower()
    product_template_json['info']['summary'] = metadatafile['description']
    product_template_json['info']['categories'][0] = dp_meta_json

    api_short = apiname + apiversion
    api_long = apiname + ":" + apiversion

    product_template_json['plans']['default-plan']['apis'] = {api_short: {}}
    product_template_json['apis'] = {api_short: {"name": api_long}}

    print(product_template_json)

    # get  draft api
    # orgs/:org/drafts/draft-apis/:draft-api-name/:draft-api-version/document
    draft_api_name = apiname
    draft_api_version = apiversion
    apic_url = APIC_ENDPOINT + "/api/orgs/" + org + "/drafts/draft-apis/" + draft_api_name + "/" + draft_api_version + "/document"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer '+ apic_token
    }

    response = requests.request("GET", apic_url, headers=headers, verify=False)

    dummy_api = json.loads(response.text)   

    # create product draft

    apic_url = APIC_ENDPOINT +  "/api/orgs/" + org + "/drafts/draft-products"

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+ apic_token
    }

    dummy_api_payload = json.dumps(dummy_api)
    product_template_json_payload = json.dumps(product_template_json)
    files = {
        'product': ('product.json', product_template_json_payload, 'application/json'),
        'openapi': ('openapi.json', dummy_api_payload, 'application/json')
    }

    response = requests.request("POST", apic_url, headers=headers, files=files, verify=False)
    product_url = json.loads(response.text)['url']
    print(product_url)

    # publish product

    catalog = APIC_CATALOG
    apic_url = APIC_ENDPOINT +  "/api/catalogs/" + org + "/" + catalog +"/publish-draft-product"


    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer '+ apic_token
    }

    payload = json.dumps({
        "draft_product_url": product_url,
        "visibility": {
            "view": {
            "type": "public"
            },
            "subscribe": {
            "type": "authenticated"
            }
        }
    })

    response = requests.request("POST", apic_url, headers=headers, data=payload, verify=False)
    resp = json.loads(response.text)
    

    return jsonify(resp)

# Get the PORT from environment
port = os.getenv('PORT', '8081')
debug = os.getenv('DEBUG', 'false')

if __name__ == '__main__':
    print("application ready - Debug is " + str(debug))
    app.run(host='0.0.0.0', port=int(port))