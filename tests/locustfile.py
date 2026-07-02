import random
from locust import HttpUser, task, between

QUERIES = [
    "How do hostel allotments work for parents?",
    "What is the CGPA requirement for a B.Tech minor?",
    "When is the Senate meeting in December 2025?",
    "Where can I apply for a minor program?",
    "What is the penalty for using heavy appliances in hostel rooms?",
    "When is the convocation in July 2026?",
    "Can a father stay in the hostel guest room?"
]

class RAGUser(HttpUser):
    # Simulated think time between student queries (1 to 3 seconds)
    wait_time = between(1, 3)

    @task(3)
    def send_query(self):
        """
        Sends random query to the FastAPI RAG query gateway.
        Simulates both cold fetches and repeating hot queries to test Redis caching.
        """
        query_text = random.choice(QUERIES)
        payload = {"query": query_text}
        
        # We wrap it in a client-block to track request results in Locust
        with self.client.post("/query", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Query request failed with status: {response.status_code}")

    @task(1)
    def health_check(self):
        """
        Polls health check route to simulate background UI checks.
        """
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status: {response.status_code}")
