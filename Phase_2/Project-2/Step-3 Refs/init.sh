# Launch Kafka Connect
/etc/confluent/docker/run &
#
# Wait for Kafka Connect listener
echo "Waiting for Kafka Connect to start listening on localhost ⏳"

while : ; do
  curl_status=$(curl -s -o /dev/null -w %{http_code} http://localhost:8083/connectors)
  echo -e $(date) " Kafka Connect listener HTTP state: " $curl_status " (waiting for 200)"
  if [ $curl_status -eq 200 ] ; then
    break
  fi
  sleep 5 
done

echo -e "\n--\n+> Configuring Kafka Connect internal topics with cleanup.policy=compact"

# Wait for Kafka to be ready
sleep 5

# Configure cleanup.policy=compact for Kafka Connect internal topics
for topic in _connect-offsets _connect-configs _connect-status; do
  echo "Configuring $topic..."
  # Delete old cleanup.policy if exists to avoid compact,delete
  kafka-configs --bootstrap-server kafka-service:29092 --alter --topic $topic --delete-config cleanup.policy 2>/dev/null || true
  # Set cleanup.policy to compact
  kafka-configs --bootstrap-server kafka-service:29092 --alter --topic $topic --add-config cleanup.policy=compact
done

echo "✓ Internal topics configured successfully"

echo -e "\n--\n+> Creating Neo4j Sink Connector"

curl -X POST http://localhost:8083/connectors/ -H "Content-Type:application/json" -H "Accept:application/json" -d @sink.neo4j.json
