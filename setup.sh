#!/bin/bash
# setup.sh - Setup script for Telegram Trading Signal Bot

set -e  # Exit on error

echo "🚀 Telegram Trading Signal Bot - Setup Script"
echo "=============================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your credentials:"
    echo "   - Get API_ID and API_HASH from https://my.telegram.org/apps"
    echo "   - Configure your channel(s)"
    echo "   - Set up trading backend credentials"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Check if .gitignore exists
if [ ! -f ".gitignore" ]; then
    echo "⚠️  Warning: .gitignore not found. Sensitive files may be committed!"
else
    echo "✅ .gitignore found"
fi
echo ""

# Run tests to verify installation
echo "🧪 Running tests to verify installation..."
if pytest tests/ -v --tb=short; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Some tests failed. This might be okay if you haven't configured everything yet."
fi
echo ""

echo "✅ Setup complete!"
echo ""
echo "📖 Next steps:"
echo "   1. Edit .env file with your credentials"
echo "   2. Run 'python GetChannelId.py' to find your channel IDs"
echo "   3. Test with DRY_RUN=true: python main.py"
echo "   4. When ready, set DRY_RUN=false and run: python main.py"
echo ""
echo "📚 For more information, see README.md"
echo ""

