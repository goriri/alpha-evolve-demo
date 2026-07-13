import logging
import time
import google.auth
import google.auth.transport.requests
import requests

logger = logging.getLogger(__name__)

def get_access_token():
    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token

def get_headers(project_id):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}",
        "x-goog-user-project": project_id
    }

def ensure_engine_and_assistant(project_id: str, engine_id: str):
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    location = "global"
    collection = "default_collection"
    
    # 1. Check if Engine exists
    engine_url = f"{base_url}/projects/{project_id}/locations/{location}/collections/{collection}/engines/{engine_id}"
    headers = get_headers(project_id)
    
    logger.info(f"Checking if engine {engine_id} exists...")
    response = requests.get(engine_url, headers=headers)
    
    if response.status_code == 200:
        logger.info(f"Engine {engine_id} already exists.")
    elif response.status_code == 404:
        logger.info(f"Engine {engine_id} not found. Creating it...")
        create_engine_url = f"{base_url}/projects/{project_id}/locations/{location}/collections/{collection}/engines?engineId={engine_id}"
        data = {
            "display_name": engine_id,
            "data_store_ids": [],
            "solution_type": "SOLUTION_TYPE_GENERATIVE_CHAT"
        }
        create_response = requests.post(create_engine_url, headers=headers, json=data)
        if create_response.status_code in (200, 201, 202):
             logger.info("Engine creation initiated. Waiting for it to be ready...")
             # Poll until it exists
             # Creating engine is async and takes a few minutes.
             # We will poll every 10 seconds for up to 5 minutes.
             for _ in range(30):
                 time.sleep(10)
                 check_response = requests.get(engine_url, headers=headers)
                 if check_response.status_code == 200:
                     logger.info("Engine is ready.")
                     break
             else:
                 raise RuntimeError("Timeout waiting for engine creation.")
        else:
             raise RuntimeError(f"Failed to create engine: {create_response.text}")
    else:
        raise RuntimeError(f"Error checking engine: {response.text}")

    # 2. Check if Assistant exists
    assistant_id = "default_assistant"
    assistant_url = f"{engine_url}/assistants/{assistant_id}"
    
    logger.info(f"Checking if assistant {assistant_id} exists under {engine_id}...")
    response = requests.get(assistant_url, headers=headers)
    
    if response.status_code == 200:
        logger.info(f"Assistant {assistant_id} already exists.")
    elif response.status_code == 404:
        logger.info(f"Assistant {assistant_id} not found. Creating it...")
        create_assistant_url = f"{engine_url}/assistants?assistantId={assistant_id}"
        data = {
            "display_name": assistant_id,
            "description": None,
            "generation_config": None,
            "web_grounding_type": "WEB_GROUNDING_TYPE_UNSPECIFIED",
            "enabled_actions": None,
            "customer_policy": None
        }
        create_response = requests.post(create_assistant_url, headers=headers, json=data)
        if create_response.status_code in (200, 201, 202):
             logger.info("Assistant created successfully.")
        else:
             raise RuntimeError(f"Failed to create assistant: {create_response.text}")
    else:
        raise RuntimeError(f"Error checking assistant: {response.text}")
