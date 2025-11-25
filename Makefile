# Makefile for Case Status Take-Home Assessment
# Usage: make [target]

.PHONY: default install run next tests clean help

# Default target - build the stack
default: install
	@echo "✅ Stack built successfully!"
	@echo "Run 'make run' to start backend or 'make next' to start frontend"

# Install all dependencies
install: install-backend install-frontend

# Install backend dependencies
install-backend:
	@echo "📦 Installing backend dependencies..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Activating virtual environment and installing packages..."
	@. .venv/bin/activate && cd case-status-interview-be && pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

# Install frontend dependencies  
install-frontend:
	@echo "📦 Installing frontend dependencies..."
	@cd case-status-interview-fe && npm install
	@echo "✅ Frontend dependencies installed"

# Run backend Flask server (eats terminal)
run:
	@echo "🚀 Starting Flask backend on http://127.0.0.1:5000"
	@echo "Press Ctrl+C to stop"
	@. .venv/bin/activate && cd case-status-interview-be && python app.py

# Run frontend Next.js server (eats terminal)
next:
	@echo "🚀 Starting Next.js frontend on http://localhost:3000"
	@echo "Press Ctrl+C to stop"
	@cd case-status-interview-fe && npm run dev

# Run unit tests
tests:
	@echo "🧪 Running unit tests..."
	@. .venv/bin/activate && cd case-status-interview-be && python -m unittest discover tests
	@echo "✅ All tests completed"

# Clean up build artifacts and dependencies
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf .venv
	@rm -rf case-status-interview-fe/node_modules
	@rm -rf case-status-interview-fe/.next
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete
	@rm -f *.db
	@echo "✅ Cleanup completed"

# Show help
help:
	@echo "Case Status Take-Home Assessment - Available Commands:"
	@echo ""
	@echo "  make          - Install all dependencies (default)"
	@echo "  make install  - Install backend and frontend dependencies"
	@echo "  make run      - Start Flask backend server (port 5000)"
	@echo "  make next     - Start Next.js frontend server (port 3000)"  
	@echo "  make tests    - Run Python unit tests"
	@echo "  make clean    - Remove all dependencies and build artifacts"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "📚 For detailed setup instructions, see SETUP_GUIDE.md"

# Development workflow targets
dev-backend: install-backend tests
	@echo "🔧 Backend ready for development"

dev-frontend: install-frontend
	@echo "🔧 Frontend ready for development"

# Quick verification that everything works
verify: install tests
	@echo "✅ Full stack verification complete"
	@echo "Both backend and frontend are ready to run"
