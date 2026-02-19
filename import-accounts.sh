#!/bin/bash

echo "🔄 Importing tdata accounts into TGsys database..."

# Build and run import container
cd /Users/admin/Desktop/TGsys/scripts
docker build -t tgsys-import -f Dockerfile.import .

# Run the import
docker run --rm \
  --network tgsys_default \
  -v /Users/admin/Desktop/TGsys/sessions:/app/sessions \
  tgsys-import

echo "✅ Account import completed!"
echo ""
echo "📊 Next steps:"
echo "1. Check Grafana dashboard: http://localhost:3000"
echo "2. Available accounts should now appear in dashboard"
echo "3. Tasks will be assigned to your accounts"
