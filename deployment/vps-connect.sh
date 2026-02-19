#!/bin/bash

# TGsys VPS Connection and Docker Setup Script
# Connects to your VPS and configures Docker + Docker Compose for TGsys

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - EDIT THESE VALUES
VPS_IP=""
VPS_USER="root"
VPS_PORT="22"
SSH_KEY=""

# TGsys Project Configuration
PROJECT_DIR="/opt/tgsys"
REPO_URL="https://github.com/ilyashumilov/TGsys.git"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

# Function to check if required tools are available
check_requirements() {
    print_info "Checking local requirements..."
    
    if ! command -v ssh &> /dev/null; then
        print_error "SSH is not installed. Please install OpenSSH client."
        exit 1
    fi
    
    if ! command -v rsync &> /dev/null; then
        print_error "rsync is not dealt.. Please install rsync."
        exit 1
    fi
    
    print_status "Requirements check passed"
}

# Function to get VPS configuration
get_vps_config() {
    print_info "Please enter your VPS connection details:"
    
    if [ -z "$VPS_IP" ]; then
        read -p "VPS IP Address: " VPS_IP
    fi
    
    if [ -z "$VPS_USER" ]; then
        read -p "SSH User (default: root): " VPS_USER_INPUT
        VPS_USER=${VPS_USER_INPUT:-root}
    fi
    
    if [ -z "$VPS_PORT" ]; then
        read -p "SSH Port (default: 22): " VPS_PORT_INPUT
        VPS_PORT=${VPS_PORT_INPUT:-22}
    fi
    
    if [ -z "$SSH_KEY" ]; then
        read -p "SSH Key Path (leave empty for password auth): " SSH_KEY
    fi
    
    echo ""
    print_info "Connection Configuration:"
    echo "  IP: $VPS_IP"
    echo "  User: $VPS_USER"
    echo "  Port: $VPS_PORT"
    echo "  SSH Key: ${SSH_KEY:-'Password Authentication'}"
    echo ""
    
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setup cancelled."
        exit 0
    fi
}

# Function to test SSH connection
test_ssh_connection() {
    print_info "Testing SSH connection to $VPS_IP..."
    
    if [ -n "$SSH_KEY" ]; then
        SSH_CMD="ssh -i $SSH_KEY -p $VPS_PORT $VPS_USER@$VPS_IP"
    else
        SSH_CMD="ssh -p $VPS_PORT $VPS_USER@$VPS_IP"
    fi
    
    if $SSH_CMD "echo 'SSH connection successful'" &>/dev/null; then
        print_status "SSH connection successful"
    else
        print_error "Failed to connect to VPS. Please check your credentials."
        exit 1
    fi
}

# Function to setup Docker on VPS
setup_docker_on_vps() {
    print_info "Setting up Docker and Docker Compose on VPS..."
    
    $SSH_CMD << 'EOF'
set -e

echo "Updating system packages..."
apt update && apt upgrade -y

echo "Installing prerequisites..."
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release git

echo "Adding Docker GPG key..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "Adding Docker repository..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing Docker..."
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo "Starting and enabling Docker..."
systemctl enable docker
systemctl start docker

echo "Adding user to docker group..."
usermod -aG docker $USER

echo "Creating project directory..."
mkdir -p $PROJECT_DIR

echo "Docker setup completed!"
EOF

    if [ $? -eq 0 ]; then
        print_status "Docker setup completed on VPS"
    else
        print_error "Docker setup failed on VPS"
        exit 1
    fi
}

# Function to deploy TGsys project
deploy_tgsys_project() {
    print_info "Deploying TGsys project to VPS..."
    
    # Clone repository on VPS
    $SSH_CMD "cd $PROJECT_DIR && git clone $REPO_URL ."
    
    if [ $? -eq 0 ]; then
        print_status "TGsys project cloned to VPS"
    else
        print_error "Failed to clone TGsys project"
        exit 1
    fi
    
    # Copy environment file if it exists locally
    if [ -f "./deployment/.env.lightweight" ]; then
        print_info "Uploading environment configuration..."
        if [ -n "$SSH_KEY" ]; then
            scp -i $SSH_KEY -P $VPS_PORT ./deployment/.env.lightweight $VPS_USER@$VPS_IP:$PROJECT_DIR/.env.lightweight
        else
            scp -P $VPS_PORT ./deployment/.env.lightweight $VPS_USER@$VPS_IP:$PROJECT_DIR/.env.lightweight
        fi
        print_status "Environment configuration uploaded"
    fi
    
    # Create necessary directories
    $SSH_CMD "cd $PROJECT_DIR && mkdir -p sessions logs backups monitoring"
    
    print_status "TGsys project deployment completed"
}

# Function to create management scripts on VPS
create_management_scripts() {
    print_info "Creating management scripts on VPS..."
    
    $SSH_CMD "cd $PROJECT_DIR && cat > deploy.sh << 'DEPLOY_EOF'
#!/bin/bash

# TGsys Deployment Management Script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e \"\${GREEN}[✓]\${NC} \$1\"
}

print_warning() {
    echo -e \"\${YELLOW}[!]\${NC} \$1\"
}

print_error() {
    echo -e \"\${RED}[✗]\${NC} \$1\"
}

# Function to deploy TGsys
deploy() {
    print_status \"Starting TGsys deployment...\"
    
    # Stop existing services
    docker-compose -f deployment/docker-compose.lightweight.yml down || true
    
    # Build and start services
    print_status \"Building and starting services...\"
    docker-compose -f deployment/docker-compose.lightweight.yml build
    docker-compose -f deployment/docker-compose.lightweight.yml up -d
    
    # Wait for services to start
    print_status \"Waiting for services to initialize...\"
    sleep 60
    
    # Check service status
    print_status \"Checking service status...\"
    docker-compose -f deployment/docker-compose.lightweight.yml ps
    
    print_status \"TGsys deployment completed!\"
}

# Function to show logs
logs() {
    docker-compose -f deployment/docker-compose.lightweight.yml logs -f
}

# Function to show status
status() {
    docker-compose -f deployment/docker-compose.lightweight.yml ps
    echo \"\"
    echo \"System Resources:\"
    echo \"Memory: \$(free -h | awk 'NR==2{printf \"%.1fGB/%.1fGB (%.0f%%)\", \$3/1024, \$2/1024, \$3*100/\$2}')\"
    echo \"Disk: \$(df -h /opt | awk 'NR==2 {print \$3\"/\"\$2\" (\"\$5\")\"}')\"
    echo \"Swap: \$(free -h | awk 'NR==3{printf \"%.1fGB/%.1fGB (%.0f%%)\", \$3/1024, \$4/1024, \$3*100/\$4}')\"
}

# Function to stop services
stop() {
    print_status \"Stopping TGsys services...\"
    docker-compose -f deployment/docker-compose.lightweight.yml down
    print_status \"Services stopped\"
}

# Function to update project
update() {
    print_status \"Updating TGsys project...\"
    
    # Pull latest changes
    git pull
    
    # Rebuild and restart
    docker-compose -f deployment/docker-compose.lightweight.yml down
    docker-compose -f deployment/docker-compose.lightweight.yml build
    docker-compose -f deployment/docker-compose.lightweight.yml up -d
    
    print_status \"TGsys updated!\"
}

# Main menu
case \"\$1\" in
    deploy)
        deploy
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    stop)
        stop
        ;;
    update)
        update
        ;;
    *)
        echo \"Usage: \$0 {deploy|logs|status|stop|update}\"
        echo \"\"
        echo \"Commands:\"
        echo \"  deploy  - Deploy TGsys services\"
        echo \"  logs    - Show TGsys logs\"
        echo \"  status  - Show service status and resources\"
        echo \"  stop    - Stop TGsys services\"
        echo \"  update  - Update TGsys to latest version\"
        exit 1
        ;;
esac
DEPLOY_EOF

chmod +x deploy.sh
chown $USER:$USER deploy.sh"
    
    print_status "Management scripts created on VPS"
}

# Function to setup firewall
setup_firewall() {
    print_info "Configuring firewall on VPS..."
    
    $SSH_CMD << 'EOF'
# Configure UFW firewall
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "Firewall configured"
EOF
    
    print_status "Firewall configured on VPS"
}

# Function to provide final instructions
provide_instructions() {
    print_info "VPS setup completed successfully!"
    echo ""
    echo "🎉 Next Steps:"
    echo "================"
    echo ""
    echo "1. Connect to your VPS:"
    if [ -n "$SSH_KEY" ]; then
        echo "   ssh -i $SSH_KEY -p $VPS_PORT $VPS_USER@$VPS_IP"
    else
        echo "   ssh -p $VPS_PORT $VPS_USER@$VPS_IP"
    fi
    echo ""
    echo "2. Navigate to project directory:"
    echo "   cd $PROJECT_DIR"
    echo ""
    echo "3. Configure environment file:"
    echo "   nano .env.lightweight"
    echo "   # Add your TELEGRAM_API_ID and TELEGRAM_API_HASH"
    echo ""
    echo "4. Deploy TGsys:"
    echo "   ./deploy.sh deploy"
    echo ""
    echo "5. Check status:"
    echo "   ./deploy.sh status"
    echo ""
    echo "📊 Management Commands:"
    echo "  ./deploy.sh status    - Check service status"
    echo "  ./deploy.sh logs      - View logs"
    echo "  ./deploy.sh stop      - Stop services"
    echo "  ./deploy.sh update    - Update project"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  docker ps              - List running containers"
    echo "  docker stats           - View resource usage"
    echo "  htop                   - System monitor"
    echo "  df -h                  - Disk usage"
    echo ""
    print_status "Your VPS is ready for TGsys deployment!"
}

# Main function
main() {
    echo "🚀 TGsys VPS Docker Setup"
    echo "========================="
    echo "This script will connect to your VPS and configure Docker + Docker Compose"
    echo ""
    
    # Run setup steps
    check_requirements
    get_vps_config
    test_ssh_connection
    setup_docker_on_vps
    setup_firewall
    deploy_tgsys_project
    create_management_scripts
    provide_instructions
    
    echo ""
    print_status "VPS setup completed successfully!"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
