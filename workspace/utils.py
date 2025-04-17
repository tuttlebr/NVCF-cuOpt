import concurrent.futures
import logging
import random
import time
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Create a custom formatter that doesn't add newlines
class SingleLineFormatter(logging.Formatter):
    """
    Custom log formatter that replaces newlines with spaces and adds a carriage return.
    
    This formatter is designed to work well in Jupyter notebooks where standard
    logging with newlines can create excessive vertical space.
    """
    def format(self, record):
        result = super().format(record)
        return result.replace("\n", " ") + "\r"


def configure_logging(level=logging.INFO):
    """
    Configure logging to display in Jupyter notebooks

    Args:
        level: Logging level (default: INFO)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicate logs
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Create console handler for Jupyter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter and add to handler
    formatter = SingleLineFormatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add handler to logger
    root_logger.addHandler(console_handler)

    return root_logger


# Configure logging by default
logger = configure_logging()


def get_optimized_routes(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    request_delay: float = 1.1,
) -> Dict[str, Any]:
    """
    Send optimization request to NVIDIA API and poll for completion.
    
    This function handles both synchronous and asynchronous responses from the API.
    If the API returns a 202 status code (Accepted), it will automatically poll
    for completion using the request ID provided in the response headers.
    
    Args:
        url: Base URL for the request
        payload: Request payload (JSON-serializable dictionary)
        headers: Request headers (defaults to standard JSON content type)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        backoff_factor: Backoff factor between retries (in seconds)
        request_delay: Delay between requests in seconds (used for rate limiting)

    Returns:
        Dict[str, Any]: JSON response from the server after successful completion
        
    Raises:
        requests.exceptions.HTTPError: If the API returns an error status code
        Exception: If polling ends with an unexpected status code
    """
    if not headers:
        headers = {"accept": "application/json", "content-type": "application/json"}
        logger.info(f"Using Default Headers: {headers}")

    # Configure session with retry strategy
    session = requests.Session()
    status_forcelist = [429, 500, 502, 503, 504, 404]
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Add artificial delay if specified
    time.sleep(request_delay)

    start_time = time.time()

    # Make initial request
    response = session.post(url, json=payload, headers=headers, timeout=timeout)
    time.sleep(request_delay)

    # Handle initial response
    response.raise_for_status()
    poll_count = 0
    request_id = response.headers.get("NVCF-REQID")
    polling_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{request_id}"

    logger.info(f"Polling NVCF Request ID: {request_id}")
    
    # Initial response status
    status_code = response.status_code
    logger.info(f"Initial response status: {status_code}")
    
    # Create a variable to store the final response
    final_response = response
    
    # Continue polling while we get 202 (Accepted/Processing)
    while status_code == 202:
        poll_count += 1
        logger.info(f"Polling attempt #{poll_count} to {polling_url}")
        
        # Wait before next poll
        time.sleep(request_delay)
        
        # Make a new poll request
        poll_response = session.get(polling_url, headers=headers, timeout=timeout)
        status_code = poll_response.status_code
        logger.info(f"Poll #{poll_count} status: {status_code}")
        
        # Check for errors
        try:
            poll_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Poll request failed: {str(e)}")
            poll_response.close()
            raise
        
        # If status is 200, the job is complete
        if status_code == 200:
            logger.info("Polling complete - job finished successfully")
            # Update our final response to be this poll response
            final_response = poll_response
            break
        
        # Close this poll response if we're going to loop again
        if status_code == 202:
            poll_response.close()
    
    # If we exited the loop without a 200 status, something went wrong
    if status_code != 200:
        logger.error(f"Polling ended with unexpected status: {status_code}")
        raise Exception(f"Unexpected status code after polling: {status_code}")

    end_time = time.time()

    # Log metrics
    logger.info(
        f"Request completed: duration={end_time - start_time:.2f}s, polls={poll_count}, "
        f"status={status_code}, size={len(final_response.content)} bytes"
    )

    return final_response.json()


def load_generator(
    num_requests: int,
    concurrency: int,
    url: str,
    payloads: List[Dict[str, Any]],
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Generate load by executing multiple requests concurrently.
    
    This function creates a thread pool and submits multiple requests to test
    the performance and reliability of the API. It randomly selects payloads
    from the provided list for each request.
    
    Args:
        num_requests: Total number of requests to make
        concurrency: Maximum number of concurrent requests (thread pool size)
        url: Target API URL
        payloads: List of request payloads to randomly select from
        **kwargs: Additional arguments passed directly to get_optimized_routes
                 (e.g., timeout, max_retries, etc.)

    Returns:
        List[Dict[str, Any]]: List of JSON responses from all successful requests
    """
    results = []
    logger.info(
        f"Starting load generator with {num_requests} requests and concurrency {concurrency}"
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []

        for _ in range(num_requests):
            # Randomly select a payload from the provided list
            payload = random.choice(payloads)

            # Submit the request
            future = executor.submit(
                get_optimized_routes, url=url, payload=payload, **kwargs
            )
            futures.append(future)

        # Collect results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                completed += 1
                logger.info(f"Completed {completed}/{num_requests} requests")
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")

    logger.info(
        f"Load generation completed. Successful requests: {len(results)}/{num_requests}"
    )
    return results


def create_from_file(file_path, is_pdp=False):
    """
    Parse optimization problem data from a text file into a pandas DataFrame.
    
    This function reads from standard CVRP or PDP format files and converts
    the data into a structured DataFrame for further processing.
    
    Args:
        file_path: Path to the input file containing problem data
        is_pdp: Whether the file is in Pickup and Delivery Problem (PDP) format.
                If False, assumes Capacitated Vehicle Routing Problem (CVRP) format.
                
    Returns:
        Tuple containing:
        - pandas.DataFrame: Node data with coordinates, time windows, etc.
        - int: Vehicle capacity
        - int: Number of vehicles
    """
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