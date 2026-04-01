import time
import requests
import interface
from neo4j import GraphDatabase
import math
import sys
import warnings
import logging
import os
from contextlib import contextmanager

# Suppress Neo4j driver warnings and notifications
warnings.filterwarnings("ignore")
logging.getLogger("neo4j").setLevel(logging.ERROR)

@contextmanager
def suppress_neo4j_notifications():
    """Context manager to suppress Neo4j server notifications"""
    # Save original stderr
    original_stderr = sys.stderr
    try:
        # Redirect stderr to devnull
        sys.stderr = open(os.devnull, 'w')
        yield
    finally:
        # Restore original stderr
        sys.stderr.close()
        sys.stderr = original_stderr

class TesterConnect:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        self._driver.verify_connectivity()

    def close(self):
        self._driver.close()

    def test_data_loaded(self):
        """
        Test to see if data is loaded into the database
            2. Run a query to get the number of nodes
            3. Run a query to get the number of edges
            4. Compare the results with the expected results
        """

        print("=" * 60)
        print("PART 1: DATA LOADING TESTS")
        print("=" * 60)

        points = 0
        total_points = 10

        with self._driver.session() as session:
            query = """
                MATCH (n)
                RETURN count(n) as num_nodes
            """
            result = session.run(query)
            num_nodes = result.data()[0]['num_nodes']

            query = """
                MATCH ()-[r]->()
                RETURN count(r) as num_edges
            """
            result = session.run(query)
            num_edges = result.data()[0]['num_edges']

            print(f"\nNode Count Test (5 points):")
            print(f"  Expected: 42 nodes")
            print(f"  Actual:   {num_nodes} nodes")
            if num_nodes == 42:
                print("  ✓ PASS [5/5 points]")
                points += 5
            else:
                print("  ✗ FAIL [0/5 points]")

            print(f"\nEdge Count Test (5 points):")
            print(f"  Expected: 1530 edges")
            print(f"  Actual:   {num_edges} edges")
            if num_edges == 1530:
                print("  ✓ PASS [5/5 points]")
                points += 5
            else:
                print("  ✗ FAIL [0/5 points]")

        print(f"\n{'─' * 60}")
        print(f"Part 1 Score: {points}/{total_points} points")
        print(f"{'─' * 60}\n")
        return points


def test_page_rank_comprehensive():
    """
    Comprehensive PageRank tests with multiple test cases
    to prevent hardcoded answers
    """

    print("=" * 60)
    print("PART 2: PAGERANK TESTS (GRADER VERSION)")
    print("=" * 60)

    points = 0
    total_points = 25
    test_cases_passed = 0
    total_test_cases = 5

    # Test Case 1: max_iterations=20, weight_property="distance"
    print(f"\n[Test 1/5] PageRank with max_iterations=20, weight='distance'")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        result = conn.pagerank(20, "distance")

        if not result or len(result) < 2:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            max_node = result[0]
            min_node = result[1]

            max_correct = max_node.get('name') == 159 and round(max_node.get('score', 0), 5) == 3.22825
            min_correct = min_node.get('name') == 59 and round(min_node.get('score', 0), 5) == 0.18247

            if max_correct and min_correct:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: max=(159, 3.22825), min=(59, 0.18247)")
                print(f"    Actual: max=({max_node.get('name')}, {round(max_node.get('score', 0), 5)}), min=({min_node.get('name')}, {round(min_node.get('score', 0), 5)})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 2: max_iterations=10, weight_property="distance"
    print(f"\n[Test 2/5] PageRank with max_iterations=10, weight='distance'")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        result = conn.pagerank(10, "distance")

        if not result or len(result) < 2:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            max_node = result[0]
            min_node = result[1]

            # Different iterations should give slightly different scores
            max_correct = max_node.get('name') == 159 and round(max_node.get('score', 0), 5) == 2.59893
            min_correct = min_node.get('name') == 59 and round(min_node.get('score', 0), 5) == 0.17706

            if max_correct and min_correct:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: max=(159, 2.59893), min=(59, 0.17706)")
                print(f"    Actual: max=({max_node.get('name')}, {round(max_node.get('score', 0), 5)}), min=({min_node.get('name')}, {round(min_node.get('score', 0), 5)})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 3: max_iterations=5, weight_property="distance"
    print(f"\n[Test 3/5] PageRank with max_iterations=5, weight='distance'")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        result = conn.pagerank(5, "distance")

        if not result or len(result) < 2:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            max_node = result[0]
            min_node = result[1]

            max_correct = max_node.get('name') == 159 and round(max_node.get('score', 0), 5) == 1.59583
            min_correct = min_node.get('name') == 59 and round(min_node.get('score', 0), 5) == 0.16844

            if max_correct and min_correct:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: max=(159, 1.59583), min=(59, 0.16844)")
                print(f"    Actual: max=({max_node.get('name')}, {round(max_node.get('score', 0), 5)}), min=({min_node.get('name')}, {round(min_node.get('score', 0), 5)})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 4: max_iterations=15, weight_property="distance"
    print(f"\n[Test 4/5] PageRank with max_iterations=15, weight='distance'")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        result = conn.pagerank(15, "distance")

        if not result or len(result) < 2:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            max_node = result[0]
            min_node = result[1]

            # Using 15 iterations gives different results
            max_correct = max_node.get('name') == 159 and round(max_node.get('score', 0), 5) == 3.03687
            min_correct = min_node.get('name') == 59 and round(min_node.get('score', 0), 5) == 0.18083

            if max_correct and min_correct:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: max=(159, 3.03687), min=(59, 0.18083)")
                print(f"    Actual: max=({max_node.get('name')}, {round(max_node.get('score', 0), 5)}), min=({min_node.get('name')}, {round(min_node.get('score', 0), 5)})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 5: max_iterations=25, weight_property="distance"
    print(f"\n[Test 5/5] PageRank with max_iterations=25, weight='distance'")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        result = conn.pagerank(25, "distance")

        if not result or len(result) < 2:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            max_node = result[0]
            min_node = result[1]

            # Using 25 iterations gives different results
            max_correct = max_node.get('name') == 159 and round(max_node.get('score', 0), 5) == 3.31188
            min_correct = min_node.get('name') == 59 and round(min_node.get('score', 0), 5) == 0.18319

            if max_correct and min_correct:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: max=(159, 3.31188), min=(59, 0.18319)")
                print(f"    Actual: max=({max_node.get('name')}, {round(max_node.get('score', 0), 5)}), min=({min_node.get('name')}, {round(min_node.get('score', 0), 5)})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Calculate points based on test cases passed
    if test_cases_passed == 5:
        points = 25
        print(f"\n  ✓ ALL TESTS PASSED [25/25 points]")
    elif test_cases_passed == 4:
        points = 20
        print(f"\n  ~ MOSTLY CORRECT [20/25 points]")
    elif test_cases_passed == 3:
        points = 15
        print(f"\n  ~ PARTIAL [15/25 points]")
    elif test_cases_passed == 2:
        points = 10
        print(f"\n  ~ MINIMAL [10/25 points]")
    elif test_cases_passed == 1:
        points = 5
        print(f"\n  ~ VERY MINIMAL [5/25 points]")
    else:
        points = 0
        print(f"\n  ✗ ALL TESTS FAILED [0/25 points]")

    print(f"\n{'─' * 60}")
    print(f"Part 2 Score: {points}/{total_points} points ({test_cases_passed}/{total_test_cases} tests passed)")
    print(f"{'─' * 60}\n")
    return points


def test_bfs_comprehensive():
    """
    Comprehensive BFS tests with multiple test cases
    to prevent hardcoded answers
    """

    print("=" * 60)
    print("PART 3: BFS TESTS (GRADER VERSION)")
    print("=" * 60)

    points = 0
    total_points = 25
    test_cases_passed = 0
    total_test_cases = 5

    # Test Case 1: 159 -> 212
    print(f"\n[Test 1/5] BFS from node 159 to node 212")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        with suppress_neo4j_notifications():
            result = conn.bfs(159, 212)

        if not result or len(result) == 0 or 'path' not in result[0]:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            first_node = result[0]['path'][0]['name']
            last_node = result[0]['path'][-1]['name']

            if first_node == 159 and last_node == 212:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL: Expected path (159 -> ... -> 212), got ({first_node} -> ... -> {last_node})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 2: 159 -> 167
    print(f"\n[Test 2/5] BFS from node 159 to node 167")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        with suppress_neo4j_notifications():
            result = conn.bfs(159, 167)

        if not result or len(result) == 0 or 'path' not in result[0]:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            first_node = result[0]['path'][0]['name']
            last_node = result[0]['path'][-1]['name']

            if first_node == 159 and last_node == 167:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL: Expected path (159 -> ... -> 167), got ({first_node} -> ... -> {last_node})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 3: 3 -> 240
    print(f"\n[Test 3/5] BFS from node 3 to node 240")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        with suppress_neo4j_notifications():
            result = conn.bfs(3, 240)

        if not result or len(result) == 0 or 'path' not in result[0]:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            first_node = result[0]['path'][0]['name']
            last_node = result[0]['path'][-1]['name']

            if first_node == 3 and last_node == 240:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL: Expected path (3 -> ... -> 240), got ({first_node} -> ... -> {last_node})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 4: 159 -> 200
    print(f"\n[Test 4/5] BFS from node 159 to node 200")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        with suppress_neo4j_notifications():
            result = conn.bfs(159, 200)

        if not result or len(result) == 0 or 'path' not in result[0]:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            first_node = result[0]['path'][0]['name']
            last_node = result[0]['path'][-1]['name']

            if first_node == 159 and last_node == 200:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL: Expected path (159 -> ... -> 200), got ({first_node} -> ... -> {last_node})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Test Case 5: 200 -> 81
    print(f"\n[Test 5/5] BFS from node 200 to node 81")
    try:
        conn = interface.Interface("neo4j://localhost:7687", "neo4j", "graphprocessing")
        with suppress_neo4j_notifications():
            result = conn.bfs(200, 81)

        if not result or len(result) == 0 or 'path' not in result[0]:
            print(f"  ✗ FAIL: Invalid return format")
        else:
            first_node = result[0]['path'][0]['name']
            last_node = result[0]['path'][-1]['name']

            if first_node == 200 and last_node == 81:
                print(f"  ✓ PASS")
                test_cases_passed += 1
            else:
                print(f"  ✗ FAIL: Expected path (200 -> ... -> 81), got ({first_node} -> ... -> {last_node})")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")

    # Calculate points based on test cases passed
    if test_cases_passed == 5:
        points = 25
        print(f"\n  ✓ ALL TESTS PASSED [25/25 points]")
    elif test_cases_passed == 4:
        points = 20
        print(f"\n  ~ MOSTLY CORRECT [20/25 points]")
    elif test_cases_passed == 3:
        points = 15
        print(f"\n  ~ PARTIAL [15/25 points]")
    elif test_cases_passed == 2:
        points = 10
        print(f"\n  ~ MINIMAL [10/25 points]")
    elif test_cases_passed == 1:
        points = 5
        print(f"\n  ~ VERY MINIMAL [5/25 points]")
    else:
        points = 0
        print(f"\n  ✗ ALL TESTS FAILED [0/25 points]")

    print(f"\n{'─' * 60}")
    print(f"Part 3 Score: {points}/{total_points} points ({test_cases_passed}/{total_test_cases} tests passed)")
    print(f"{'─' * 60}\n")
    return points


def main():

    count = 0
    print("\n" + "=" * 60)
    print("PROJECT 1: GRADER VERSION - COMPREHENSIVE TESTS")
    print("=" * 60)
    print("\n⚠️  WARNING: This is the grader version with multiple test cases")
    print("   to prevent hardcoded solutions.\n")
    print("Connecting to Neo4j server", end="")
    sys.stdout.flush()

    while count < 10:
        try:
            response = requests.get("http://localhost:7474/")
            print(" ✓")
            print("Server is running!\n")
            break
        except:
            print(".", end="")
            sys.stdout.flush()
            count += 1
            time.sleep(5)

    if count == 10:
        print("\n\n✗ ERROR: Could not connect to Neo4j server")
        print("Please ensure Docker container is running")
        return

    # Initialize scores
    total_score = 0

    # Test load data
    tester = TesterConnect("neo4j://localhost:7687", "neo4j", "graphprocessing")
    score_part1 = tester.test_data_loaded()
    total_score += score_part1
    tester.close()

    # Test PageRank (comprehensive)
    score_part2 = test_page_rank_comprehensive()
    total_score += score_part2

    # Test BFS (comprehensive)
    score_part3 = test_bfs_comprehensive()
    total_score += score_part3

    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL SCORE SUMMARY (GRADER VERSION)")
    print("=" * 60)
    print(f"\nPart 1 - Data Loading:     {score_part1}/10 points")
    print(f"Part 2 - PageRank:         {score_part2}/25 points (5 test cases)")
    print(f"Part 3 - BFS:              {score_part3}/25 points (5 test cases)")
    print(f"\n{'─' * 60}")
    print(f"TOTAL SCORE:               {total_score}/60 points")
    print(f"{'─' * 60}")
    print(f"\nNote: Dockerfile configuration worth 40 points is graded separately")
    print("      Total project points: 100")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
