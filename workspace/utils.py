import concurrent.futures
import logging
import random
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_optimized_routes(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    fetch_url_format: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    request_delay: float = 0.0,
) -> Dict[str, Any]:
    """
    Load generator function for route optimization requests

    Args:
        url: Base URL for the request
        payload: Request payload
        headers: Request headers
        fetch_url_format: Format string for polling URL
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        backoff_factor: Backoff factor between retries
        request_delay: Delay between requests in seconds

    Returns:
        JSON response from the server
    """
    if not headers:
        headers = {"accept": "application/json", "content-type": "application/json"}

    # Configure session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        # Add artificial delay if specified
        if request_delay > 0:
            time.sleep(request_delay)

        start_time = time.time()
        response = session.post(url, json=payload, headers=headers, timeout=timeout)

        # Poll for completion if necessary
        poll_count = 0
        while response.status_code == 202:
            request_id = response.headers.get("NVCF-REQID")
            if not request_id or not fetch_url_format:
                raise ValueError("Missing request ID or fetch URL format")

            fetch_url = fetch_url_format + request_id
            poll_count += 1

            if request_delay > 0:
                time.sleep(request_delay)

            response = session.get(fetch_url, headers=headers, timeout=timeout)

        response.raise_for_status()
        end_time = time.time()

        # Log metrics
        logging.info(
            {
                "request_duration": end_time - start_time,
                "poll_count": poll_count,
                "status_code": response.status_code,
                "response_size": len(response.content),
            }
        )

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        raise

    finally:
        session.close()


def load_generator(
    num_requests: int, concurrency: int, url: str, payloads: List[Dict[str, Any]], **kwargs
) -> List[Dict[str, Any]]:
    """
    Generate load by executing multiple requests concurrently

    Args:
        num_requests: Total number of requests to make
        concurrency: Maximum number of concurrent requests
        url: Target URL
        payloads: List of request payloads to use
        **kwargs: Additional arguments to pass to get_optimized_routes

    Returns:
        List of responses from all successful requests
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []

        for _ in range(num_requests):
            # Randomly select a payload from the provided list
            payload = random.choice(payloads)

            # Submit the request
            future = executor.submit(get_optimized_routes, url=url, payload=payload, **kwargs)
            futures.append(future)

        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logging.error(f"Request failed: {str(e)}")

    return results


def create_from_file(file_path, is_pdp=False):
    node_list = []
    with open(file_path, "rt") as f:
        count = 1
        for line in f:
            if is_pdp and count == 1:
                vehicle_num, vehicle_capacity, speed = line.split()
            elif not is_pdp and count == 5:
                vehicle_num, vehicle_capacity = line.split()
            elif is_pdp:
                node_list.append(line.split())
            elif count >= 10:
                node_list.append(line.split())
            count += 1
            # if count == 36:
            #     break

    vehicle_num = int(vehicle_num)
    vehicle_capacity = int(vehicle_capacity)
    df = pd.DataFrame(
        columns=[
            "vertex",
            "xcord",
            "ycord",
            "demand",
            "earliest_time",
            "latest_time",
            "service_time",
            "pickup_index",
            "delivery_index",
        ]
    )

    for item in node_list:
        row = {
            "vertex": int(item[0]),
            "xcord": float(item[1]),
            "ycord": float(item[2]),
            "demand": int(item[3]),
            "earliest_time": int(item[4]),
            "latest_time": int(item[5]),
            "service_time": int(item[6]),
        }
        if is_pdp:
            row["pickup_index"] = int(item[7])
            row["delivery_index"] = int(item[8])
        df = pd.concat([df, pd.DataFrame(row, index=[0])], ignore_index=True)

    return df, vehicle_capacity, vehicle_num
