import time
import random
import uuid
from prometheus_client import start_http_server, Counter, Gauge, Histogram, Info, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR

# Unregister default metrics (like resident memory) to prevent conflicts with our mocks
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(GC_COLLECTOR)

# Define labels for the basic metrics
LABELS = {
    'method': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'],
    'endpoint': ['/api/v1/users', '/api/v1/login', '/api/v1/query', '/api/v1/metrics', '/health', '/api/v1/logout', '/api/v1/settings'],
    'status': ['200', '201', '400', '401', '500', '403', '404'],
    'tenant': ['t1', 't2', 't3', 't4', 't5', 't6', 't7'],
    'region': ['us-east', 'us-west', 'eu-central', 'eu-west', 'ap-south', 'ap-east', 'sa-east']
}

# The original mock metrics
REQUESTS = Counter('mock_http_requests_total', 'Total number of HTTP requests made.', list(LABELS.keys()))
DURATION = Counter('mock_http_request_duration_seconds_total', 'Total duration of HTTP requests in seconds.', list(LABELS.keys()))

# --- New metrics for the 20 queries ---

# 1, 6, 11, 12, 13, 14, 15: http_requests_total & http_request_duration_seconds
HTTP_REQUESTS_TOTAL = Counter('http_requests_total', 'Total HTTP requests', ['service', 'instance1', 'status', 'job1'])
HTTP_REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['job1', 'instance1'])

# 2: process_resident_memory_bytes
PROCESS_RESIDENT_MEMORY = Gauge('process_resident_memory_bytes', 'Resident memory size in bytes', ['instance1'])

# 3: container_cpu_usage_seconds_total
CONTAINER_CPU_USAGE = Counter('container_cpu_usage_seconds_total', 'Container CPU usage', ['pod', 'instance1'])

# 4: node_memory_MemFree_bytes, node_memory_MemTotal_bytes
NODE_MEM_FREE = Gauge('node_memory_MemFree_bytes', 'Node memory free', ['instance1'])
NODE_MEM_TOTAL = Gauge('node_memory_MemTotal_bytes', 'Node memory total', ['instance1'])

# 5: kube_pod_status_phase
KUBE_POD_STATUS = Gauge('kube_pod_status_phase', 'Pod standing phase', ['pod', 'instance1', 'phase'])

# 7: node_filesystem_avail_bytes
NODE_FS_AVAIL = Gauge('node_filesystem_avail_bytes', 'Filesystem available bytes', ['instance1'])

# 8: build_version_info
BUILD_VERSION = Info('build_version', 'Build version info')

# 9: rabbitmq_queue_messages
RABBITMQ_MSGS = Gauge('rabbitmq_queue_messages', 'RabbitMQ queue messages', ['instance1'])

# 10: process_start_time_seconds
PROCESS_START_TIME = Gauge('process_start_time_seconds', 'Process start time', ['instance1'])

# 14, 16, 17: up
UP = Gauge('up', 'Is job up', ['job1', 'instance1', 'host'])

# 18: network_rx_bytes
NETWORK_RX = Counter('network_rx_bytes', 'Network RX bytes', ['instance1'])

# 19: node_network_transmit_bytes_total
NODE_NETWORK_TX = Counter('node_network_transmit_bytes_total', 'Network TX bytes', ['instance1'])

# 20: node_cpu_seconds_total
NODE_CPU = Counter('node_cpu_seconds_total', 'Node CPU seconds', ['instance1', 'mode'])


def generate_traffic():
    """Generates random traffic across all permutations of labels."""
    
    # Initialize some states
    BUILD_VERSION.info({'version': '1.2.3', 'revision': 'abcdef'})
    
    pods = ['pod-1', 'pod-2', 'pod-3', 'pod-4', 'pod-5']
    instances = ['node1', 'node2', 'node3', 'node4', 'node5']
    jobs = ['web', 'api', 'db', 'critical-worker-node']
    
    for inst in instances:
        NODE_MEM_TOTAL.labels(instance1=inst).set(16 * 1024 * 1024 * 1024) # 16GB
        PROCESS_START_TIME.labels(instance1=inst).set(time.time() - random.randint(1000, 100000))
        UP.labels(job1=random.choice(jobs), instance1=inst, host=f"host-{inst}").set(1)
        
        for pod in pods:
            KUBE_POD_STATUS.labels(pod=pod, instance1=inst, phase='Running').set(1)

    while True:
        # Original mock data
        method = random.choice(LABELS['method'])
        endpoint = random.choice(LABELS['endpoint'])
        status_val = random.choice(LABELS['status'])
        tenant = random.choice(LABELS['tenant'])
        region = random.choice(LABELS['region'])
        
        requests_inc = random.randint(1, 10)
        duration_inc = requests_inc * random.uniform(0.01, 0.5)
        
        REQUESTS.labels(method=method, endpoint=endpoint, status=status_val, tenant=tenant, region=region).inc(requests_inc)
        DURATION.labels(method=method, endpoint=endpoint, status=status_val, tenant=tenant, region=region).inc(duration_inc)
        
        # New metrics data
        inst = random.choice(instances)
        job = random.choice(jobs)
        pod = random.choice(pods)
        
        HTTP_REQUESTS_TOTAL.labels(service='my-service', instance1=inst, status=status_val, job1=job).inc(random.randint(1, 5))
        HTTP_REQUEST_DURATION.labels(job1=job, instance1=inst).observe(random.expovariate(10)) # average 0.1s
        
        PROCESS_RESIDENT_MEMORY.labels(instance1=inst).set(random.randint(100, 500) * 1024 * 1024)
        CONTAINER_CPU_USAGE.labels(pod=pod, instance1=inst).inc(random.uniform(0.01, 0.1))
        
        NODE_MEM_FREE.labels(instance1=inst).set(random.randint(1, 8) * 1024 * 1024 * 1024)
        NODE_FS_AVAIL.labels(instance1=inst).set(random.randint(10, 100) * 1024 * 1024 * 1024)
        
        RABBITMQ_MSGS.labels(instance1=inst).set(random.randint(0, 1000))
        
        NETWORK_RX.labels(instance1=inst).inc(random.randint(1000, 50000))
        NODE_NETWORK_TX.labels(instance1=inst).inc(random.randint(1000, 50000))
        
        NODE_CPU.labels(instance1=inst, mode='idle').inc(random.uniform(0.5, 1.0))
        NODE_CPU.labels(instance1=inst, mode='user').inc(random.uniform(0.01, 0.2))
        NODE_CPU.labels(instance1=inst, mode='system').inc(random.uniform(0.01, 0.1))

        # Simulate some processing delay
        time.sleep(random.uniform(0.01, 0.1))

if __name__ == '__main__':
    # Start the Prometheus metrics server on port 8001
    print("Starting Prometheus mock metrics server on port 8001...")
    start_http_server(8001)
    
    # Run the traffic generator loop
    generate_traffic()
