#!/bin/bash

# Grafana API setup script
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin"

echo "Setting up Grafana datasource..."

# Create Prometheus datasource
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $(echo -n "$GRAFANA_USER:$GRAFANA_PASSWORD" | base64)" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true,
    "editable": true
  }' \
  "$GRAFANA_URL/api/datasources"

echo "Datasource created. Now you can import the dashboard."
