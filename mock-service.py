import time
import random
from prometheus_client import start_http_server, Counter

# Define our 5 labels and their 5 unique values each
LABELS = {
    'method': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    'endpoint': ['/api/v1/users', '/api/v1/login', '/api/v1/query', '/api/v1/metrics', '/health'],
    'status': ['200', '201', '400', '401', '500'],
    'tenant': ['t1', 't2', 't3', 't4', 't5'],
    'region': ['us-east', 'us-west', 'eu-central', 'eu-west', 'ap-south']
}

# Create a single Counter metric with the 5 labels
REQUESTS = Counter(
    name='mock_http_requests_total',
    documentation='Total number of HTTP requests made.',
    labelnames=list(LABELS.keys())
)

# Create a second Counter metric for duration to allow for vector matching
DURATION = Counter(
    name='mock_http_request_duration_seconds_total',
    documentation='Total duration of HTTP requests in seconds.',
    labelnames=list(LABELS.keys())
)

def generate_traffic():
    """Generates random traffic across all permutations of labels."""
    while True:
        # Pick a random combination of labels
        method = random.choice(LABELS['method'])
        endpoint = random.choice(LABELS['endpoint'])
        status = random.choice(LABELS['status'])
        tenant = random.choice(LABELS['tenant'])
        region = random.choice(LABELS['region'])
        
        # Increment the counter for this unique combination
        requests_inc = random.randint(1, 10)
        duration_inc = requests_inc * random.uniform(0.01, 0.5) # Simulate varying processing times
        
        REQUESTS.labels(
            method=method,
            endpoint=endpoint,
            status=status,
            tenant=tenant,
            region=region
        ).inc(requests_inc)
        
        DURATION.labels(
            method=method,
            endpoint=endpoint,
            status=status,
            tenant=tenant,
            region=region
        ).inc(duration_inc)
        
        # Simulate some processing delay
        time.sleep(random.uniform(0.01, 0.1))

if __name__ == '__main__':
    # Initialize all 3125 possible time series combinations to 0
    # This ensures they exist in Prometheus immediately with a value of 0
    for method in LABELS['method']:
        for endpoint in LABELS['endpoint']:
            for status in LABELS['status']:
                for tenant in LABELS['tenant']:
                    for region in LABELS['region']:
                        REQUESTS.labels(
                            method=method,
                            endpoint=endpoint,
                            status=status,
                            tenant=tenant,
                            region=region
                        ).inc(0)
                        
                        DURATION.labels(
                            method=method,
                            endpoint=endpoint,
                            status=status,
                            tenant=tenant,
                            region=region
                        ).inc(0.0)

    # Start the Prometheus metrics server on port 8001
    print("Starting Prometheus mock metrics server on port 8001...")
    start_http_server(8001)
    
    # Run the traffic generator loop
    generate_traffic()
