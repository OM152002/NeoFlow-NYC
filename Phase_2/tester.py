#!/usr/bin/env python3
"""
Comprehensive Test Suite for Kafka-Neo4j Pipeline
Tests each component according to grader.md workflow
"""

import subprocess
import time
import json
import sys
from typing import Dict, List, Tuple
from confluent_kafka import Producer, Consumer, KafkaException
from neo4j import GraphDatabase
import pyarrow.parquet as pq


class PipelineTestSuite:
    """Test suite with rubric-based scoring"""

    def __init__(self):
        self.results = {}
        self.total_score = 0
        self.max_score = 100
        self.kafka_bootstrap = 'localhost:9092'
        self.neo4j_uri = 'bolt://localhost:7687'
        self.neo4j_user = 'neo4j'
        self.neo4j_password = 'processingpipeline'
        self.topic_name = 'nyc_taxicab_data'

    def print_header(self, text: str):
        """Print formatted test section header"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)

    def print_test(self, name: str, status: str, points: int, max_points: int, details: str = ""):
        """Print individual test result"""
        symbol = "✓" if status == "PASS" else "✗"
        print(f"\n{symbol} {name}")
        print(f"   Score: {points}/{max_points} points")
        if details:
            print(f"   Details: {details}")

    def run_kubectl_command(self, cmd: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """Execute kubectl command and return success status"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

    # ========================================================================
    # STEP 1: KUBERNETES INFRASTRUCTURE TESTS (30 points)
    # ========================================================================

    def test_step1_zookeeper_deployment(self) -> Dict:
        """Test Zookeeper deployment (10 points)"""
        self.print_header("STEP 1.1: Testing Zookeeper Deployment")
        score = 0
        max_score = 10

        # Test 1.1: Zookeeper deployment exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'deployment', 'zookeeper-deployment'])
        if success:
            score += 3
            self.print_test("Zookeeper Deployment Exists", "PASS", 3, 3)
        else:
            self.print_test("Zookeeper Deployment Exists", "FAIL", 0, 3, output)

        # Test 1.2: Zookeeper service exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'service', 'zookeeper-service'])
        if success:
            score += 3
            self.print_test("Zookeeper Service Exists", "PASS", 3, 3)
        else:
            self.print_test("Zookeeper Service Exists", "FAIL", 0, 3, output)

        # Test 1.3: Zookeeper pod is running
        success, output = self.run_kubectl_command(
            ['kubectl', 'get', 'pods', '-l', 'app=zookeeper', '-o', 'jsonpath={.items[0].status.phase}']
        )
        if success and 'Running' in output:
            score += 4
            self.print_test("Zookeeper Pod Running", "PASS", 4, 4)
        else:
            self.print_test("Zookeeper Pod Running", "FAIL", 0, 4, output)

        return {"score": score, "max_score": max_score, "details": "Zookeeper infrastructure"}

    def test_step1_kafka_deployment(self) -> Dict:
        """Test Kafka deployment (10 points)"""
        self.print_header("STEP 1.2: Testing Kafka Deployment")
        score = 0
        max_score = 10

        # Test 1.4: Kafka deployment exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'deployment', 'kafka-deployment'])
        if success:
            score += 3
            self.print_test("Kafka Deployment Exists", "PASS", 3, 3)
        else:
            self.print_test("Kafka Deployment Exists", "FAIL", 0, 3, output)

        # Test 1.5: Kafka service exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'service', 'kafka-service'])
        if success:
            score += 3
            self.print_test("Kafka Service Exists", "PASS", 3, 3)
        else:
            self.print_test("Kafka Service Exists", "FAIL", 0, 3, output)

        # Test 1.6: Kafka pod is running
        success, output = self.run_kubectl_command(
            ['kubectl', 'get', 'pods', '-l', 'app=kafka', '-o', 'jsonpath={.items[0].status.phase}']
        )
        if success and 'Running' in output:
            score += 4
            self.print_test("Kafka Pod Running", "PASS", 4, 4)
        else:
            self.print_test("Kafka Pod Running", "FAIL", 0, 4, output)

        return {"score": score, "max_score": max_score, "details": "Kafka infrastructure"}

    def test_step1_kafka_connectivity(self) -> Dict:
        """Test Kafka connectivity (10 points)"""
        self.print_header("STEP 1.3: Testing Kafka Connectivity")
        score = 0
        max_score = 10

        try:
            # Wait for port-forward to be established (manual step)
            print("\n⚠️  Make sure port-forwarding is active:")
            print("   kubectl port-forward svc/kafka-service 9092:9092")
            time.sleep(2)

            # Test Kafka connection
            conf = {'bootstrap.servers': self.kafka_bootstrap}
            producer = Producer(conf)

            # Get cluster metadata
            metadata = producer.list_topics(timeout=10)

            if metadata:
                score += 10
                self.print_test("Kafka Connection Successful", "PASS", 10, 10,
                              f"Found {len(metadata.topics)} topics")
            else:
                self.print_test("Kafka Connection Successful", "FAIL", 0, 10)

        except Exception as e:
            self.print_test("Kafka Connection Successful", "FAIL", 0, 10, str(e))

        return {"score": score, "max_score": max_score, "details": "Kafka connectivity"}

    # ========================================================================
    # STEP 2: NEO4J TESTS (15 points)
    # ========================================================================

    def test_step2_neo4j_deployment(self) -> Dict:
        """Test Neo4j deployment (8 points)"""
        self.print_header("STEP 2.1: Testing Neo4j Deployment")
        score = 0
        max_score = 8

        # Test 2.1: Neo4j helm release exists
        success, output = self.run_kubectl_command(['helm', 'list'])
        if success and 'my-neo4j-release' in output:
            score += 4
            self.print_test("Neo4j Helm Release Exists", "PASS", 4, 4)
        else:
            self.print_test("Neo4j Helm Release Exists", "FAIL", 0, 4, output)

        # Test 2.2: Neo4j service exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'service', 'neo4j-service'])
        if success:
            score += 4
            self.print_test("Neo4j Service Exists", "PASS", 4, 4)
        else:
            self.print_test("Neo4j Service Exists", "FAIL", 0, 4, output)

        return {"score": score, "max_score": max_score, "details": "Neo4j deployment"}

    def test_step2_neo4j_connectivity(self) -> Dict:
        """Test Neo4j connectivity (7 points)"""
        self.print_header("STEP 2.2: Testing Neo4j Connectivity")
        score = 0
        max_score = 7

        try:
            print("\n⚠️  Make sure port-forwarding is active:")
            print("   kubectl port-forward svc/neo4j-service 7474:7474 7687:7687")
            time.sleep(2)

            # Connect to Neo4j
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                if result.single()["test"] == 1:
                    score += 7
                    self.print_test("Neo4j Connection Successful", "PASS", 7, 7)
                else:
                    self.print_test("Neo4j Connection Successful", "FAIL", 0, 7)

            driver.close()

        except Exception as e:
            self.print_test("Neo4j Connection Successful", "FAIL", 0, 7, str(e))

        return {"score": score, "max_score": max_score, "details": "Neo4j connectivity"}

    # ========================================================================
    # STEP 3: KAFKA-NEO4J CONNECTOR TESTS (15 points)
    # ========================================================================

    def test_step3_connector_deployment(self) -> Dict:
        """Test Kafka-Neo4j connector deployment (15 points)"""
        self.print_header("STEP 3: Testing Kafka-Neo4j Connector")
        score = 0
        max_score = 15

        # Test 3.1: Connector deployment exists
        success, output = self.run_kubectl_command(['kubectl', 'get', 'deployment', 'kafka-neo4j-connector'])
        if success:
            score += 7
            self.print_test("Connector Deployment Exists", "PASS", 7, 7)
        else:
            self.print_test("Connector Deployment Exists", "FAIL", 0, 7, output)

        # Test 3.2: Connector pod is running
        success, output = self.run_kubectl_command(
            ['kubectl', 'get', 'pods', '-l', 'app=kafka-neo4j-connector', '-o', 'jsonpath={.items[0].status.phase}']
        )
        if success and 'Running' in output:
            score += 8
            self.print_test("Connector Pod Running", "PASS", 8, 8)
        else:
            self.print_test("Connector Pod Running", "FAIL", 0, 8, output)

        return {"score": score, "max_score": max_score, "details": "Kafka-Neo4j connector"}

    # ========================================================================
    # STEP 4: DATA LOADING TESTS (20 points)
    # ========================================================================

    def test_step4_data_file(self) -> Dict:
        """Test data file exists and is valid (5 points)"""
        self.print_header("STEP 4.1: Testing Data File")
        score = 0
        max_score = 5

        try:
            # Check if parquet file exists
            trips = pq.read_table('yellow_tripdata_2022-03.parquet')
            trips_df = trips.to_pandas()

            if len(trips_df) > 0:
                score += 5
                self.print_test("Parquet File Valid", "PASS", 5, 5,
                              f"Contains {len(trips_df)} rows")
            else:
                self.print_test("Parquet File Valid", "FAIL", 0, 5, "File is empty")

        except Exception as e:
            self.print_test("Parquet File Valid", "FAIL", 0, 5, str(e))

        return {"score": score, "max_score": max_score, "details": "Data file validation"}

    def test_step4_data_producer_structure(self) -> Dict:
        """Test data_producer.py structure (15 points)"""
        self.print_header("STEP 4.2: Testing Data Producer Script")
        score = 0
        max_score = 15

        try:
            with open('data_producer.py', 'r') as f:
                content = f.read()

            # Test 4.2: Imports are correct
            required_imports = ['confluent_kafka', 'Producer', 'pyarrow']
            if all(imp in content for imp in required_imports):
                score += 3
                self.print_test("Required Imports Present", "PASS", 3, 3)
            else:
                self.print_test("Required Imports Present", "FAIL", 0, 3)

            # Test 4.3: Kafka producer configuration
            if 'bootstrap.servers' in content and 'localhost:9092' in content:
                score += 3
                self.print_test("Kafka Configuration Correct", "PASS", 3, 3)
            else:
                self.print_test("Kafka Configuration Correct", "FAIL", 0, 3)

            # Test 4.4: Topic name is correct
            if 'nyc_taxicab_data' in content:
                score += 3
                self.print_test("Topic Name Correct", "PASS", 3, 3)
            else:
                self.print_test("Topic Name Correct", "FAIL", 0, 3)

            # Test 4.5: Bronx filtering logic
            if 'bronx' in content.lower() and 'PULocationID' in content and 'DOLocationID' in content:
                score += 3
                self.print_test("Bronx Filtering Present", "PASS", 3, 3)
            else:
                self.print_test("Bronx Filtering Present", "FAIL", 0, 3)

            # Test 4.6: Message production logic
            if 'producer.produce' in content and 'producer.flush' in content:
                score += 3
                self.print_test("Message Production Logic", "PASS", 3, 3)
            else:
                self.print_test("Message Production Logic", "FAIL", 0, 3)

        except Exception as e:
            self.print_test("Data Producer Script", "FAIL", 0, max_score, str(e))

        return {"score": score, "max_score": max_score, "details": "Data producer validation"}

    # ========================================================================
    # STEP 5: END-TO-END PIPELINE TEST (20 points)
    # ========================================================================

    def test_step5_kafka_messages(self) -> Dict:
        """Test messages in Kafka topic (10 points)"""
        self.print_header("STEP 5.1: Testing Kafka Message Production")
        score = 0
        max_score = 10

        try:
            # Configure consumer
            conf = {
                'bootstrap.servers': self.kafka_bootstrap,
                'group.id': 'test_consumer_group',
                'auto.offset.reset': 'earliest'
            }

            consumer = Consumer(conf)
            consumer.subscribe([self.topic_name])

            messages = []
            timeout = 5
            start_time = time.time()

            print(f"\n📥 Consuming messages from topic '{self.topic_name}' (timeout: {timeout}s)...")

            while time.time() - start_time < timeout:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    continue

                messages.append(msg.value().decode('utf-8'))
                if len(messages) >= 5:  # Sample 5 messages
                    break

            consumer.close()

            if len(messages) > 0:
                score += 10
                self.print_test("Messages in Kafka Topic", "PASS", 10, 10,
                              f"Found {len(messages)} messages")

                # Show sample message
                try:
                    sample = json.loads(messages[0])
                    print(f"\n   Sample message: {json.dumps(sample, indent=2)[:200]}...")
                except:
                    print(f"\n   Sample message: {messages[0][:200]}...")
            else:
                self.print_test("Messages in Kafka Topic", "FAIL", 0, 10,
                              "No messages found. Did you run data_producer.py?")

        except Exception as e:
            self.print_test("Messages in Kafka Topic", "FAIL", 0, 10, str(e))

        return {"score": score, "max_score": max_score, "details": "Kafka message validation"}

    def test_step5_neo4j_data(self) -> Dict:
        """Test data in Neo4j (10 points)"""
        self.print_header("STEP 5.2: Testing Neo4j Data Ingestion")
        score = 0
        max_score = 10

        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Count nodes
                result = session.run("MATCH (n) RETURN count(n) AS count")
                count = result.single()["count"]

                if count > 0:
                    score += 10
                    self.print_test("Data in Neo4j", "PASS", 10, 10,
                                  f"Found {count} nodes")

                    # Sample some data
                    result = session.run("MATCH (n) RETURN n LIMIT 1")
                    sample = result.single()
                    if sample:
                        print(f"\n   Sample node: {dict(sample['n'])}")
                else:
                    self.print_test("Data in Neo4j", "FAIL", 0, 10,
                                  "No data found. Connector may not be working.")

            driver.close()

        except Exception as e:
            self.print_test("Data in Neo4j", "FAIL", 0, 10, str(e))

        return {"score": score, "max_score": max_score, "details": "Neo4j data validation"}

    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================

    def run_all_tests(self):
        """Run all tests and generate report"""
        self.print_header("NYC TAXI DATA PIPELINE - COMPREHENSIVE TEST SUITE")
        print("This test suite validates all components according to grader.md")

        test_results = []

        # Step 1: Infrastructure (30 points)
        test_results.append(self.test_step1_zookeeper_deployment())
        test_results.append(self.test_step1_kafka_deployment())
        test_results.append(self.test_step1_kafka_connectivity())

        # Step 2: Neo4j (15 points)
        test_results.append(self.test_step2_neo4j_deployment())
        test_results.append(self.test_step2_neo4j_connectivity())

        # Step 3: Connector (15 points)
        test_results.append(self.test_step3_connector_deployment())

        # Step 4: Data Loading (20 points)
        test_results.append(self.test_step4_data_file())
        test_results.append(self.test_step4_data_producer_structure())

        # Step 5: End-to-End (20 points)
        test_results.append(self.test_step5_kafka_messages())
        test_results.append(self.test_step5_neo4j_data())

        # Generate final report
        self.generate_report(test_results)

    def generate_report(self, test_results: List[Dict]):
        """Generate final test report with rubric"""
        self.print_header("FINAL TEST REPORT & RUBRIC")

        total_score = sum(r["score"] for r in test_results)
        total_max = sum(r["max_score"] for r in test_results)
        percentage = (total_score / total_max * 100) if total_max > 0 else 0

        print("\n📊 SCORE BREAKDOWN:")
        print("-" * 70)

        categories = {
            "Infrastructure (Zookeeper + Kafka)": test_results[0:3],
            "Neo4j Deployment": test_results[3:5],
            "Kafka-Neo4j Connector": test_results[5:6],
            "Data Loading": test_results[6:8],
            "End-to-End Pipeline": test_results[8:10]
        }

        for category, results in categories.items():
            cat_score = sum(r["score"] for r in results)
            cat_max = sum(r["max_score"] for r in results)
            print(f"\n{category}:")
            print(f"  Score: {cat_score}/{cat_max} points")
            for r in results:
                print(f"    - {r['details']}: {r['score']}/{r['max_score']}")

        print("\n" + "=" * 70)
        print(f"TOTAL SCORE: {total_score}/{total_max} ({percentage:.1f}%)")
        print("=" * 70)

        # Grade assignment
        if percentage >= 90:
            grade = "A"
        elif percentage >= 80:
            grade = "B"
        elif percentage >= 70:
            grade = "C"
        elif percentage >= 60:
            grade = "D"
        else:
            grade = "F"

        print(f"\nFINAL GRADE: {grade}")

        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if total_score < total_max:
            print("\nAreas needing attention:")
            for i, result in enumerate(test_results):
                if result["score"] < result["max_score"]:
                    print(f"  - {result['details']}")
        else:
            print("  ✓ All tests passed! Pipeline is fully functional.")

        return total_score, total_max


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║     NYC TAXI DATA PIPELINE - AUTOMATED TEST SUITE                 ║
║     Tests infrastructure, data flow, and end-to-end pipeline      ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    print("\n⚠️  PREREQUISITES:")
    print("   1. Minikube must be running")
    print("   2. All deployments must be applied:")
    print("      - kubectl apply -f zookeeper-setup.yaml")
    print("      - kubectl apply -f kafka-setup.yaml")
    print("      - helm install my-neo4j-release neo4j/neo4j -f neo4j-values.yaml")
    print("      - kubectl apply -f neo4j-service.yaml")
    print("      - kubectl apply -f kafka-neo4j-connector.yaml")
    print("   3. Port forwarding must be active in separate terminals:")
    print("      - kubectl port-forward svc/kafka-service 9092:9092")
    print("      - kubectl port-forward svc/neo4j-service 7474:7474 7687:7687")
    print("\n")

    input("Press Enter when ready to start tests...")

    # Run tests
    suite = PipelineTestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()
